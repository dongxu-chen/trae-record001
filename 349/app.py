from flask import Flask, request, jsonify
from typing import Dict, Any

from config import (
    CREDIT_SCORE_MIN, CREDIT_SCORE_MAX, RISK_LEVELS,
    get_rating_thresholds, load_rating_thresholds, save_rating_thresholds,
    update_rating_threshold, get_industry_baseline, get_industry_config,
    INDUSTRY_MONITORING_CONFIG, INDUSTRY_RISK_BASELINES
)
from data.models import (
    CompanyInput, CreditScoreResponse, RiskFactor,
    MonitoringAlert, PostLoanMonitoringResponse
)
from data.generate_data import generate_company, generate_training_data
from kg.neo4j_client import (
    Neo4jClient, create_company_graph, extract_kg_features,
    create_supply_chain_relation, create_legal_relation,
    get_time_decay_info
)
from kg.relation_graph import (
    build_enterprise_graph, export_graph_for_visualization,
    get_graph_summary
)
from model.feature_engineering import (
    build_feature_vector, score_to_rating, score_to_risk_level, compute_ground_truth_score
)
from model.training import (
    train_model, predict_score, get_feature_importance,
    load_model, load_feature_names, prepare_training_data
)
from model.score_simulator import get_simulator
from analysis.risk_analysis import (
    analyze_risk_factors, get_key_strengths, get_risk_warnings,
    get_category_contributions, generate_recommendation, create_explainer, save_explainer
)
from analysis.migration_matrix import get_migration_analyzer
from monitoring.post_loan import get_monitor

app = Flask(__name__)

_monitor = get_monitor()
_simulator = get_simulator()
_migration_analyzer = get_migration_analyzer()


def _safe_extract_kg_features(company_id: str) -> Dict[str, float]:
    try:
        return extract_kg_features(company_id)
    except Exception:
        return {
            "shareholder_count": 1.0,
            "avg_share_ratio": 0.5,
            "shareholder_other_companies": 0.0,
            "corporate_shareholder_count": 0.0,
            "shareholder_quality_score": 50.0,
            "executive_count": 1.0,
            "avg_executive_tenure": 3.0,
            "industry_peer_count": 0.0,
            "industry_peer_score": 50.0,
            "supply_chain_partners": 0.0,
            "avg_supply_strength": 0.0,
            "supply_chain_stability_score": 50.0,
            "legal_relation_count": 0.0,
            "total_legal_lawsuits": 0.0,
            "legal_relation_score": 80.0,
            "associated_companies": 0.0,
            "associated_executives": 0.0,
            "association_risk_score": 60.0,
        }


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Enterprise Credit Rating System",
        "version": "3.0.0"
    })


@app.route("/api/company/graph", methods=["POST"])
def get_company_graph():
    try:
        data = request.get_json()
        company = CompanyInput(**data)
        max_depth = data.get("max_depth", 2)
        include_types = data.get("include_types", None)
        export_format = data.get("format", "json")

        graph = build_enterprise_graph(company, max_depth, include_types)

        if export_format == "cytoscape":
            result = export_graph_for_visualization(graph, "cytoscape")
        elif export_format == "graphviz":
            result = export_graph_for_visualization(graph, "graphviz")
        else:
            result = export_graph_for_visualization(graph, "json")

        summary = get_graph_summary(graph)

        return jsonify({
            "company_id": company.business_info.company_id,
            "company_name": company.business_info.company_name,
            "graph": result,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/company/graph/summary", methods=["POST"])
def get_company_graph_summary():
    try:
        data = request.get_json()
        company = CompanyInput(**data)
        max_depth = data.get("max_depth", 2)

        graph = build_enterprise_graph(company, max_depth)
        summary = get_graph_summary(graph)

        return jsonify({
            "company_id": company.business_info.company_id,
            "summary": summary,
            "central_entities": summary.get("key_entities", []),
            "high_risk_relations": summary.get("high_risk_relations_count", 0)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulation/factors", methods=["GET"])
def get_simulation_factors():
    try:
        factors = _simulator.get_adjustable_factors()
        return jsonify({
            "adjustable_factors": factors,
            "total_categories": len(factors),
            "total_factors": sum(len(v) for v in factors.values())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulation/simulate", methods=["POST"])
def simulate_score():
    try:
        data = request.get_json()
        company = CompanyInput(**data.get("company", {}))
        adjustments = data.get("adjustments", {})
        kg_features = _safe_extract_kg_features(company.business_info.company_id)

        result = _simulator.simulate(company, kg_features, adjustments)

        return jsonify({
            "company_id": company.business_info.company_id,
            "simulation_result": result.__dict__
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulation/multi-scenario", methods=["POST"])
def simulate_multi_scenario():
    try:
        data = request.get_json()
        company = CompanyInput(**data.get("company", {}))
        scenarios = data.get("scenarios", [])
        kg_features = _safe_extract_kg_features(company.business_info.company_id)

        results = _simulator.simulate_multiple_scenarios(company, kg_features, scenarios)

        return jsonify({
            "company_id": company.business_info.company_id,
            "scenarios_count": len(scenarios),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulation/optimization", methods=["POST"])
def get_optimization_suggestions():
    try:
        data = request.get_json()
        company = CompanyInput(**data.get("company", {}))
        target_score = float(data.get("target_score", 700))
        kg_features = _safe_extract_kg_features(company.business_info.company_id)

        suggestions = _simulator.get_optimization_suggestions(company, kg_features, target_score)

        from model.training import predict_score
        current_score = predict_score(company, kg_features)

        return jsonify({
            "company_id": company.business_info.company_id,
            "current_score": round(current_score, 2),
            "target_score": target_score,
            "score_gap": round(target_score - current_score, 2),
            "suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/migration/matrix", methods=["GET"])
def get_migration_matrix():
    try:
        industry = request.args.get("industry", "default")
        period = request.args.get("period", "1年")

        matrix = _migration_analyzer.get_migration_matrix(industry, period)

        return jsonify({
            "industry": industry,
            "period": period,
            "matrix": matrix.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/migration/forecast", methods=["POST"])
def get_migration_forecast():
    try:
        data = request.get_json()
        company = CompanyInput(**data.get("company", {}))
        current_score = float(data.get("current_score", 500))
        forecast_years = data.get("forecast_years", [1, 3, 5])

        forecast = _migration_analyzer.get_company_migration_forecast(
            company, current_score, forecast_years
        )

        return jsonify(forecast.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/migration/summary/<rating>", methods=["GET"])
def get_migration_summary(rating: str):
    try:
        industry = request.args.get("industry", "default")

        summary = _migration_analyzer.get_multi_year_migration_summary(rating, industry)

        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/migration/heatmap", methods=["GET"])
def get_migration_heatmap():
    try:
        industry = request.args.get("industry", "default")

        heatmap = _migration_analyzer.calculate_transition_heatmap(industry)

        return jsonify(heatmap)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/credit/score", methods=["POST"])
def credit_score():
    try:
        data = request.get_json()
        company = CompanyInput(**data)

        try:
            create_company_graph(company)
        except Exception:
            pass

        kg_features = _safe_extract_kg_features(company.business_info.company_id)

        model, scaler = load_model()
        score = predict_score(company, kg_features, model, scaler)

        risk_factors = analyze_risk_factors(company, kg_features, score)
        key_strengths = get_key_strengths(risk_factors)
        risk_warnings = get_risk_warnings(risk_factors)
        category_contrib = get_category_contributions(risk_factors)
        recommendation = generate_recommendation(risk_factors, score)

        rating = score_to_rating(score)
        risk_level = score_to_risk_level(score)

        top_risk_factors = risk_factors[:10]

        feature_contribs = []
        for rf in top_risk_factors:
            feature_contribs.append({
                "feature": rf["feature"],
                "description": rf["description"],
                "category": rf["category"],
                "impact": rf["impact"],
                "direction": rf["direction"],
                "severity": rf["severity"],
            })

        industry = company.business_info.industry
        industry_baseline = get_industry_baseline(industry)

        response = CreditScoreResponse(
            company_id=company.business_info.company_id,
            credit_score=round(score, 2),
            rating=rating,
            risk_level=risk_level,
            risk_factors=top_risk_factors,
            key_strengths=key_strengths,
            recommendation=recommendation,
            feature_contributions=feature_contribs
        )

        result = response.model_dump()
        result["industry"] = industry
        result["industry_baseline"] = industry_baseline

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Credit scoring failed"
        }), 500


@app.route("/api/credit/rating/<rating>", methods=["GET"])
def get_rating_info(rating: str):
    thresholds = get_rating_thresholds()
    if rating in thresholds:
        low, high = thresholds[rating]
        return jsonify({
            "rating": rating,
            "score_range": f"{low}-{high}",
            "risk_level": RISK_LEVELS.get(rating, "未知"),
            "description": _get_rating_description(rating)
        })
    return jsonify({"error": f"Unknown rating: {rating}"}), 404


@app.route("/api/credit/rating-thresholds", methods=["GET"])
def get_all_rating_thresholds():
    thresholds = get_rating_thresholds()
    result = {}
    for rating, (low, high) in thresholds.items():
        result[rating] = {
            "lower": low,
            "upper": high,
            "risk_level": RISK_LEVELS.get(rating, "未知")
        }
    return jsonify({"thresholds": result})


@app.route("/api/credit/rating-thresholds", methods=["PUT"])
def update_rating_thresholds():
    try:
        data = request.get_json()
        if "thresholds" in data:
            new_thresholds = {}
            for rating, bounds in data["thresholds"].items():
                if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
                    new_thresholds[rating] = (float(bounds[0]), float(bounds[1]))
                elif isinstance(bounds, dict):
                    new_thresholds[rating] = (float(bounds["lower"]), float(bounds["upper"]))
            save_rating_thresholds(new_thresholds)
            return jsonify({
                "status": "success",
                "message": "Rating thresholds updated",
                "thresholds": {k: [v[0], v[1]] for k, v in new_thresholds.items()}
            })
        elif "rating" in data:
            rating = data["rating"]
            lower = float(data.get("lower", 0))
            upper = float(data.get("upper", 1000))
            updated = update_rating_threshold(rating, lower, upper)
            return jsonify({
                "status": "success",
                "message": f"Rating {rating} updated",
                "rating": rating,
                "new_bounds": [lower, upper]
            })
        else:
            return jsonify({"error": "Must provide 'thresholds' or 'rating' with bounds"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/credit/feature-importance", methods=["GET"])
def feature_importance():
    try:
        model, _ = load_model()
        importance = get_feature_importance(model)
        return jsonify({
            "feature_importance": importance,
            "top_10": dict(list(importance.items())[:10])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/register", methods=["POST"])
def register_loan():
    try:
        data = request.get_json()
        company_id = data["company_id"]
        baseline_score = float(data.get("baseline_score", 500))
        industry = data.get("industry", "default")

        _monitor.register_loan(company_id, baseline_score, industry)

        industry_config = get_industry_config(industry)
        industry_baseline = get_industry_baseline(industry)

        return jsonify({
            "status": "success",
            "message": f"Loan registered for company {company_id}",
            "baseline_score": baseline_score,
            "industry": industry,
            "industry_baseline": industry_baseline,
            "industry_config": {
                "score_drop_alert_threshold": industry_config.get("score_drop_alert_threshold"),
                "score_warning_threshold": industry_config.get("score_warning_threshold"),
                "check_interval_days": industry_config.get("check_interval_days"),
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/update", methods=["POST"])
def update_monitoring():
    try:
        data = request.get_json()
        company_id = data["company_id"]

        if "new_score" in data:
            new_score = float(data["new_score"])
            alerts = _monitor.update_score(company_id, new_score)
            return jsonify({
                "status": "success",
                "company_id": company_id,
                "new_score": new_score,
                "alerts_generated": len(alerts),
                "alerts": alerts
            })
        elif "event_type" in data:
            event_type = data["event_type"]
            description = data.get("description", "")
            alert = _monitor.report_negative_event(company_id, event_type, description)
            return jsonify({
                "status": "success",
                "company_id": company_id,
                "alert": alert
            })
        else:
            return jsonify({"error": "Must provide new_score or event_type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/report/<company_id>", methods=["GET"])
def monitoring_report(company_id: str):
    try:
        report = _monitor.generate_monitoring_report(company_id)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/industry-warning-lines", methods=["GET"])
def get_industry_warning_lines():
    try:
        lines = _monitor.get_industry_warning_lines()
        return jsonify({
            "industry_warning_lines": lines
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/industry-config/<industry>", methods=["GET"])
def get_industry_monitoring_config(industry: str):
    try:
        config = get_industry_config(industry)
        baseline = get_industry_baseline(industry)
        return jsonify({
            "industry": industry,
            "config": config,
            "baseline": baseline,
            "warning_line": round(
                baseline.get("baseline_score", 600) - baseline.get("baseline_score", 600) * baseline.get("volatility", 0.18), 1
            ),
            "critical_line": round(
                baseline.get("baseline_score", 600) - baseline.get("baseline_score", 600) * baseline.get("volatility", 0.18) * 1.5, 1
            )
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/monitoring/alerts", methods=["GET"])
def get_alerts():
    company_id = request.args.get("company_id")
    alert_level = request.args.get("alert_level")

    alerts = _monitor.get_all_alerts(company_id, alert_level)
    return jsonify({
        "total_alerts": len(alerts),
        "alerts": alerts
    })


@app.route("/api/monitoring/alerts/<alert_id>/dismiss", methods=["POST"])
def dismiss_alert(alert_id: str):
    success = _monitor.dismiss_alert(alert_id)
    if success:
        return jsonify({"status": "success", "message": "Alert dismissed"})
    return jsonify({"error": "Alert not found"}), 404


@app.route("/api/company/sample", methods=["GET"])
def generate_sample():
    risk_level = request.args.get("risk_level", "medium")
    company_id = request.args.get("company_id")
    company_name = request.args.get("company_name")

    company = generate_company(risk_level, company_id, company_name)
    return jsonify(company.model_dump())


@app.route("/api/company/kg/build", methods=["POST"])
def build_kg():
    try:
        data = request.get_json()
        company = CompanyInput(**data)
        relation_date = data.get("relation_date")

        create_company_graph(company, relation_date)

        return jsonify({
            "status": "success",
            "message": f"Knowledge graph built for {company.business_info.company_id}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/company/kg/features/<company_id>", methods=["GET"])
def get_kg_features(company_id: str):
    try:
        features = extract_kg_features(company_id)
        return jsonify({
            "company_id": company_id,
            "kg_features": features
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/company/kg/time-decay-info", methods=["GET"])
def get_kg_time_decay_info():
    return jsonify(get_time_decay_info())


@app.route("/api/company/kg/supply-chain", methods=["POST"])
def add_supply_chain():
    try:
        data = request.get_json()
        create_supply_chain_relation(
            data["company_id"],
            data["related_company_id"],
            data.get("relation_type", "supplier"),
            data.get("strength", 0.5),
            data.get("relation_date")
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/company/kg/legal-relation", methods=["POST"])
def add_legal_relation():
    try:
        data = request.get_json()
        create_legal_relation(
            data["company_id"],
            data["related_company_id"],
            data.get("lawsuit_count", 0),
            data.get("relation_date")
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/model/train", methods=["POST"])
def train_endpoint():
    try:
        data = request.get_json()
        n_samples = data.get("n_samples", 500)

        companies = generate_training_data(n_samples)
        kg_features_list = []
        for company in companies:
            kg_features = _safe_extract_kg_features(company.business_info.company_id)
            kg_features_list.append(kg_features)

        model, scaler = train_model(companies, kg_features_list)

        X, y = prepare_training_data(companies, kg_features_list)
        X_scaled = scaler.transform(X)
        predictions = model.predict(X_scaled)
        mae = float((abs(predictions - y)).mean())
        rmse = float(((predictions - y) ** 2).mean() ** 0.5)

        return jsonify({
            "status": "success",
            "n_samples": n_samples,
            "metrics": {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
            },
            "message": "Model trained and saved successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/model/explainer/init", methods=["POST"])
def init_explainer():
    try:
        data = request.get_json()
        n_background = data.get("n_background", 100)

        companies = generate_training_data(n_background)
        kg_features_list = []
        for company in companies:
            kg_features = _safe_extract_kg_features(company.business_info.company_id)
            kg_features_list.append(kg_features)

        model, scaler = load_model()
        X, _ = prepare_training_data(companies, kg_features_list)
        X_scaled = scaler.transform(X)

        explainer = create_explainer(model, X_scaled)
        save_explainer(explainer)

        return jsonify({
            "status": "success",
            "message": "SHAP explainer initialized and saved"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_rating_description(rating: str) -> str:
    descriptions = {
        "AAA": "信用极好，偿债能力极强，几乎无违约风险",
        "AA": "信用优秀，偿债能力很强，违约风险极低",
        "A": "信用良好，偿债能力较强，违约风险低",
        "BBB": "信用较好，偿债能力尚可，违约风险较低",
        "BB": "信用一般，偿债能力一般，存在一定违约风险",
        "B": "信用较差，偿债能力较弱，违约风险较高",
        "CCC": "信用差，偿债能力弱，违约风险高",
        "CC": "信用很差，偿债能力很弱，违约风险很高",
        "C": "信用极差，偿债能力极弱，违约风险极高",
        "D": "信用极差，已出现违约或濒临破产",
    }
    return descriptions.get(rating, "未知评级")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
