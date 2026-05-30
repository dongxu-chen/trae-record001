import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from config.config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    FEATURE_COLUMNS, MULTI_OBJECTIVE_WEIGHTS
)
from models.lightgbm_model import LambdaMARTRanker
from features.text_matching import compute_all_features
from evaluation.metrics import ndcg_at_k
from personalization.user_profile import PersonalizationEngine
from online_learning.online_learner import OnlineLearner
from multi_objective.multi_objective_ranker import MultiObjectiveScorer


def create_app():
    app = Flask(__name__)

    ranker = LambdaMARTRanker()
    pers_engine = PersonalizationEngine()
    online_learner = OnlineLearner(feature_columns=FEATURE_COLUMNS)
    mo_ranker = MultiObjectiveScorer(weights=MULTI_OBJECTIVE_WEIGHTS)

    try:
        ranker.load_model()
        app.logger.info("Loaded LambdaMART model successfully")
    except Exception as e:
        app.logger.warning(f"No pre-trained model found: {e}")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "model_loaded": ranker.is_loaded(),
            "personalization_engine": True,
            "online_learner": True,
            "multi_objective": True,
        })

    @app.route("/rank", methods=["POST"])
    def rank():
        data = request.get_json()
        if not data or "query" not in data or "products" not in data:
            return jsonify({"error": "Missing 'query' or 'products' field"}), 400

        query = data["query"]
        products = data["products"]
        if not products:
            return jsonify({"error": "No products provided"}), 400

        if not ranker.is_loaded():
            return jsonify({"error": "Model not loaded. Train first."}), 503

        user_id = data.get("user_id")
        enable_personalization = data.get("enable_personalization", False)
        enable_multi_objective = data.get("enable_multi_objective", False)
        mo_weights = data.get("mo_weights", MULTI_OBJECTIVE_WEIGHTS)

        price_list = [p.get("price", 0) for p in products]

        feature_list = []
        for product in products:
            feats = compute_all_features(query, product, price_list=price_list)

            if enable_personalization and user_id:
                pers_feats = pers_engine.compute_personalization_features(user_id, product)
                feats.update(pers_feats)

            feature_list.append(feats)

        X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in feature_list])
        raw_scores, probabilities = ranker.predict_with_scores(X)

        if enable_multi_objective:
            temp_mo = MultiObjectiveScorer(weights=mo_weights)
            ranked_products, final_scores, obj_scores = temp_mo.rank_products(
                products, raw_scores, method="weighted"
            )
        else:
            final_scores = raw_scores
            sorted_indices = np.argsort(-final_scores)
            ranked_products = [products[i] for i in sorted_indices]
            obj_scores = None

        results = []
        for i, product in enumerate(ranked_products):
            result = {
                "product_id": product.get("product_id", f"p_{i}"),
                "title": product.get("title", ""),
                "relevance_score": float(product.get("multi_objective_score", raw_scores[i])),
                "relevance_probability": float(probabilities[i]),
                "rank": i + 1,
            }
            if "objective_scores" in product:
                result["objective_scores"] = product["objective_scores"]
            results.append(result)

        return jsonify({
            "query": query,
            "user_id": user_id,
            "personalization_enabled": enable_personalization,
            "multi_objective_enabled": enable_multi_objective,
            "ranked_products": results,
            "total": len(results),
        })

    @app.route("/personalize/rank", methods=["POST"])
    def personalize_rank():
        data = request.get_json()
        if not data or "user_id" not in data or "query" not in data or "products" not in data:
            return jsonify({"error": "Missing 'user_id', 'query', or 'products' field"}), 400

        user_id = data["user_id"]
        query = data["query"]
        products = data["products"]
        personalization_weight = data.get("personalization_weight", 0.3)

        if not ranker.is_loaded():
            return jsonify({"error": "Model not loaded. Train first."}), 503

        price_list = [p.get("price", 0) for p in products]

        feature_list = []
        for product in products:
            feats = compute_all_features(query, product, price_list=price_list)
            pers_feats = pers_engine.compute_personalization_features(user_id, product)
            feats.update(pers_feats)
            feature_list.append(feats)

        X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in feature_list])
        base_scores = ranker.predict(X)

        reranked_products, reranked_scores = pers_engine.rerank_with_personalization(
            user_id, products, base_scores, personalization_weight
        )

        user_profile = pers_engine.get_or_create_user(user_id)
        profile_data = {
            "user_id": user_id,
            "top_categories": user_profile.get_top_categories(5),
            "top_brands": user_profile.get_top_brands(5),
            "click_count": len(user_profile.click_history),
            "purchase_count": len(user_profile.purchase_history),
        }

        results = []
        for i, (product, score) in enumerate(zip(reranked_products, reranked_scores)):
            results.append({
                "product_id": product.get("product_id", f"p_{i}"),
                "title": product.get("title", ""),
                "final_score": float(score),
                "rank": i + 1,
            })

        return jsonify({
            "query": query,
            "user_profile": profile_data,
            "personalization_weight": personalization_weight,
            "ranked_products": results,
            "total": len(results),
        })

    @app.route("/user/profile", methods=["GET"])
    def get_user_profile():
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing 'user_id' parameter"}), 400

        user_profile = pers_engine.get_or_create_user(user_id)
        return jsonify({
            "user_id": user_id,
            "top_categories": user_profile.get_top_categories(10),
            "top_brands": user_profile.get_top_brands(10),
            "price_range": user_profile.price_range,
            "click_count": len(user_profile.click_history),
            "purchase_count": len(user_profile.purchase_history),
            "browse_count": len(user_profile.browse_history),
        })

    @app.route("/user/feedback", methods=["POST"])
    def record_user_feedback():
        data = request.get_json()
        if not data or "user_id" not in data or "product" not in data or "action" not in data:
            return jsonify({"error": "Missing 'user_id', 'product', or 'action' field"}), 400

        user_id = data["user_id"]
        product = data["product"]
        action = data["action"]
        timestamp = data.get("timestamp")

        if action == "click":
            pers_engine.record_click(user_id, product, timestamp)
        elif action == "purchase":
            pers_engine.record_purchase(user_id, product, timestamp)
        elif action == "browse":
            pers_engine.record_browse(user_id, product, timestamp)
        else:
            return jsonify({"error": "Invalid action. Must be 'click', 'purchase', or 'browse'"}), 400

        online_learner.record_feedback(
            query=data.get("query", ""),
            product=product,
            position=data.get("position", 0),
            clicked=(action == "click"),
            dwell_time=data.get("dwell_time", 0),
        )

        return jsonify({"status": "success", "action": action, "user_id": user_id})

    @app.route("/online/feedback", methods=["POST"])
    def record_click_feedback():
        data = request.get_json()
        if not data or "query" not in data or "products" not in data:
            return jsonify({"error": "Missing 'query' or 'products' field"}), 400

        query = data["query"]
        products = data["products"]
        clicked_positions = data.get("clicked_positions", [])
        dwell_times = data.get("dwell_times", [])

        for i, product in enumerate(products):
            clicked = i in clicked_positions
            dwell = dwell_times[i] if i < len(dwell_times) else 0
            online_learner.record_feedback(
                query=query,
                product=product,
                position=i,
                clicked=clicked,
                dwell_time=dwell,
            )

        stats = online_learner.get_stats()
        return jsonify({
            "status": "success",
            "feedback_recorded": len(products),
            "total_feedback": stats["total_feedback"],
        })

    @app.route("/online/stats", methods=["GET"])
    def get_online_stats():
        stats = online_learner.get_stats()
        return jsonify(stats)

    @app.route("/online/update", methods=["POST"])
    def trigger_online_update():
        def feature_extractor(query, product):
            feats = compute_all_features(query, product)
            return feats

        updated = online_learner.update_model(feature_extractor)
        stats = online_learner.get_stats()

        return jsonify({
            "model_updated": updated,
            "stats": stats,
        })

    @app.route("/multi_objective/rank", methods=["POST"])
    def multi_objective_rank():
        data = request.get_json()
        if not data or "query" not in data or "products" not in data:
            return jsonify({"error": "Missing 'query' or 'products' field"}), 400

        query = data["query"]
        products = data["products"]
        weights = data.get("weights", MULTI_OBJECTIVE_WEIGHTS)
        method = data.get("method", "weighted")

        if not ranker.is_loaded():
            return jsonify({"error": "Model not loaded. Train first."}), 503

        price_list = [p.get("price", 0) for p in products]

        feature_list = []
        for product in products:
            feats = compute_all_features(query, product, price_list=price_list)
            feature_list.append(feats)

        X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in feature_list])
        base_scores = ranker.predict(X)

        temp_mo = MultiObjectiveScorer(weights=weights)
        ranked_products, final_scores, obj_scores = temp_mo.rank_products(
            products, base_scores, method=method
        )

        results = []
        for i, product in enumerate(ranked_products):
            results.append({
                "product_id": product.get("product_id", f"p_{i}"),
                "title": product.get("title", ""),
                "final_score": float(product["multi_objective_score"]),
                "objective_scores": product["objective_scores"],
                "rank": i + 1,
            })

        return jsonify({
            "query": query,
            "method": method,
            "weights": weights,
            "ranked_products": results,
            "total": len(results),
        })

    @app.route("/multi_objective/weights", methods=["GET", "POST"])
    def manage_weights():
        if request.method == "POST":
            data = request.get_json()
            new_weights = data.get("weights", MULTI_OBJECTIVE_WEIGHTS)
            mo_ranker.weights = new_weights
            return jsonify({"status": "updated", "weights": mo_ranker.weights})
        else:
            return jsonify({"weights": mo_ranker.weights, "default_weights": MULTI_OBJECTIVE_WEIGHTS})

    @app.route("/search", methods=["POST"])
    def search():
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' field"}), 400

        query = data["query"]
        size = data.get("size", 20)
        user_id = data.get("user_id")
        enable_personalization = data.get("enable_personalization", False)
        enable_multi_objective = data.get("enable_multi_objective", False)

        try:
            from search_engine import ElasticsearchClient
            es_client = ElasticsearchClient()
            products = es_client.search_with_bm25(query, size=size)
        except Exception as e:
            return jsonify({"error": f"Elasticsearch error: {str(e)}"}), 503

        if not products:
            return jsonify({"query": query, "ranked_products": [], "total": 0})

        if not ranker.is_loaded():
            sorted_products = sorted(products, key=lambda x: x.get("es_bm25_score", 0), reverse=True)
            return jsonify({
                "query": query,
                "ranked_products": sorted_products,
                "total": len(sorted_products),
                "ranking_method": "bm25_fallback",
            })

        price_list = [p.get("price", 0) for p in products]
        feature_list = []
        for product in products:
            feats = compute_all_features(query, product, price_list=price_list)

            if enable_personalization and user_id:
                pers_feats = pers_engine.compute_personalization_features(user_id, product)
                feats.update(pers_feats)

            feature_list.append(feats)

        X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in feature_list])
        raw_scores = ranker.predict(X)

        if enable_multi_objective:
            ranked_products, final_scores, obj_scores = mo_ranker.rank_products(
                products, raw_scores, method="weighted"
            )
        else:
            sorted_indices = np.argsort(-raw_scores)
            ranked_products = [products[i] for i in sorted_indices]

        for i, product in enumerate(ranked_products):
            product["relevance_score"] = float(raw_scores[i])
            product["rank"] = i + 1

        return jsonify({
            "query": query,
            "user_id": user_id,
            "personalization_enabled": enable_personalization,
            "multi_objective_enabled": enable_multi_objective,
            "ranked_products": ranked_products,
            "total": len(ranked_products),
            "ranking_method": "lambdamart" + ("+mo" if enable_multi_objective else ""),
        })

    @app.route("/evaluate", methods=["POST"])
    def evaluate():
        data = request.get_json()
        if not data or "query" not in data or "products" not in data:
            return jsonify({"error": "Missing 'query' or 'products' field"}), 400

        query = data["query"]
        products = data["products"]

        if not ranker.is_loaded():
            return jsonify({"error": "Model not loaded"}), 503

        price_list = [p.get("price", 0) for p in products]
        feature_list = []
        labels = []
        for product in products:
            feats = compute_all_features(query, product, price_list=price_list)
            feature_list.append(feats)
            labels.append(product.get("relevance_label", 0))

        X = np.array([[f.get(col, 0.0) for col in FEATURE_COLUMNS] for f in feature_list])
        predictions = ranker.predict(X)

        sorted_indices = np.argsort(-predictions)
        sorted_labels = [labels[i] for i in sorted_indices]

        results = {
            "NDCG@1": ndcg_at_k(sorted_labels, 1),
            "NDCG@3": ndcg_at_k(sorted_labels, 3),
            "NDCG@5": ndcg_at_k(sorted_labels, 5),
            "NDCG@10": ndcg_at_k(sorted_labels, 10),
        }

        return jsonify({
            "query": query,
            "metrics": results,
            "num_products": len(products),
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
