import os
import sys
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MultiObjectiveScorer:
    def __init__(self, weights=None):
        self.weights = weights or {
            "relevance": 0.5,
            "conversion": 0.3,
            "freshness": 0.2,
        }
        self.objective_names = ["relevance", "conversion", "freshness"]

    def normalize_scores(self, scores):
        if len(scores) == 0:
            return scores
        scores = np.array(scores, dtype=np.float64)
        min_score = scores.min()
        max_score = scores.max()
        if max_score == min_score:
            return np.ones_like(scores) * 0.5
        return (scores - min_score) / (max_score - min_score)

    def compute_relevance_score(self, base_score):
        return base_score

    def compute_conversion_score(self, product):
        conv_rate = product.get("conversion_rate", 0.0)
        ctr = product.get("ctr_7d", product.get("click_rate", 0.0))
        cart_rate = product.get("cart_rate", 0.0)
        sales_volume = min(product.get("sales_volume", 0) / 10000.0, 1.0)
        review_score = product.get("review_score", 0.0) / 5.0

        conv_score = (
            conv_rate * 0.4 +
            ctr * 0.25 +
            cart_rate * 0.15 +
            sales_volume * 0.1 +
            review_score * 0.1
        )
        return min(conv_score, 1.0)

    def compute_freshness_score(self, product, current_days=None):
        if current_days is None:
            import time
            current_days = time.time() / 86400

        launch_days = product.get("launch_days", current_days)
        days_since_launch = max(current_days - launch_days, 1)

        half_life = 90
        freshness = np.exp(-np.log(2) * days_since_launch / half_life)

        recent_sales_ratio = product.get("sales_recency_ratio", 1.0)
        recent_sales_ratio = min(recent_sales_ratio, 2.0) / 2.0

        click_trend = product.get("click_trend", 1.0)
        click_trend = min(click_trend, 2.0) / 2.0

        freshness_combined = (
            freshness * 0.5 +
            recent_sales_ratio * 0.3 +
            click_trend * 0.2
        )
        return min(freshness_combined, 1.0)

    def score_objectives(self, products, base_scores):
        n = len(products)
        scores_by_objective = {
            "relevance": [],
            "conversion": [],
            "freshness": [],
        }

        for i, product in enumerate(products):
            scores_by_objective["relevance"].append(
                self.compute_relevance_score(base_scores[i])
            )
            scores_by_objective["conversion"].append(
                self.compute_conversion_score(product)
            )
            scores_by_objective["freshness"].append(
                self.compute_freshness_score(product)
            )

        for obj in self.objective_names:
            scores_by_objective[obj] = self.normalize_scores(
                scores_by_objective[obj]
            )

        return scores_by_objective

    def weighted_linear_combination(self, scores_by_objective, weights=None):
        if weights is None:
            weights = self.weights

        n = len(scores_by_objective["relevance"])
        combined_scores = np.zeros(n)

        for obj, w in weights.items():
            combined_scores += w * np.array(scores_by_objective[obj])

        return combined_scores

    def pareto_ranking(self, scores_by_objective):
        n = len(scores_by_objective["relevance"])
        scores = np.column_stack([
            scores_by_objective[obj] for obj in self.objective_names
        ])

        dominated = np.zeros(n, dtype=bool)

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if np.all(scores[j] >= scores[i]) and np.any(scores[j] > scores[i]):
                    dominated[i] = True
                    break

        pareto_ranks = np.zeros(n)
        current_rank = 1

        while not np.all(dominated):
            non_dominated = ~dominated
            pareto_ranks[non_dominated] = current_rank
            dominated[non_dominated] = True
            current_rank += 1

        return pareto_ranks

    def rank_products(self, products, base_scores, method="weighted", weights=None):
        scores_by_objective = self.score_objectives(products, base_scores)

        if method == "weighted":
            final_scores = self.weighted_linear_combination(scores_by_objective, weights)
        elif method == "pareto":
            pareto_ranks = self.pareto_ranking(scores_by_objective)
            avg_score = self.weighted_linear_combination(scores_by_objective, weights)
            final_scores = -pareto_ranks + avg_score * 0.1
        elif method == "minimax":
            min_scores = np.min([
                scores_by_objective[obj] for obj in self.objective_names
            ], axis=0)
            final_scores = min_scores
        else:
            final_scores = self.weighted_linear_combination(scores_by_objective, weights)

        sorted_indices = np.argsort(-final_scores)
        ranked_products = [products[i] for i in sorted_indices]
        ranked_scores = [final_scores[i] for i in sorted_indices]

        for i, product in enumerate(ranked_products):
            product["multi_objective_score"] = float(ranked_scores[i])
            product["objective_scores"] = {
                obj: float(scores_by_objective[obj][sorted_indices[i]])
                for obj in self.objective_names
            }

        return ranked_products, ranked_scores, scores_by_objective

    def tune_weights(self, products, base_scores, target_ctr, target_conv_rate,
                      learning_rate=0.01, num_iterations=100):
        current_weights = self.weights.copy()
        best_weights = current_weights.copy()
        best_objective = float("inf")

        for _ in range(num_iterations):
            ranked_products, scores, _ = self.rank_products(
                products, base_scores, method="weighted", weights=current_weights
            )

            top_5_indices = [p["product_id"] for p in ranked_products[:5]]
            avg_conv = np.mean([
                self.compute_conversion_score(p) for p in ranked_products[:10]
            ])
            avg_fresh = np.mean([
                self.compute_freshness_score(p) for p in ranked_products[:10]
            ])

            ctr_error = (target_ctr - base_scores[0]) ** 2
            conv_error = (target_conv_rate - avg_conv) ** 2

            objective = ctr_error + conv_error

            if objective < best_objective:
                best_objective = objective
                best_weights = current_weights.copy()

            grad_rel = 2 * (base_scores[0] - target_ctr) * base_scores[0]
            grad_conv = 2 * (avg_conv - target_conv_rate) * avg_conv

            current_weights["relevance"] -= learning_rate * grad_rel
            current_weights["conversion"] -= learning_rate * grad_conv
            current_weights["freshness"] = max(0.1, 1 - current_weights["relevance"] - current_weights["conversion"])

            total = sum(current_weights.values())
            for k in current_weights:
                current_weights[k] /= total

        self.weights = best_weights
        return best_weights

    def print_objective_breakdown(self, products, base_scores, top_n=5):
        scores_by_objective = self.score_objectives(products, base_scores)
        weighted_scores = self.weighted_linear_combination(scores_by_objective)

        sorted_indices = np.argsort(-weighted_scores)[:top_n]

        print("\n  Multi-Objective Score Breakdown (Top {}):".format(top_n))
        print("  {:<5} {:<35} {:<10} {:<10} {:<10} {:<10}".format(
            "Rank", "Product", "Relevance", "Conversion", "Freshness", "Final"))
        print("  " + "-" * 70)

        for rank, idx in enumerate(sorted_indices, 1):
            p = products[idx]
            print("  {:<5} {:<35} {:<10.4f} {:<10.4f} {:<10.4f} {:<10.4f}".format(
                rank,
                p.get("title", "")[:33],
                scores_by_objective["relevance"][idx],
                scores_by_objective["conversion"][idx],
                scores_by_objective["freshness"][idx],
                weighted_scores[idx]
            ))


def create_balanced_scorer(mode="balanced"):
    if mode == "relevance_first":
        weights = {"relevance": 0.7, "conversion": 0.2, "freshness": 0.1}
    elif mode == "conversion_first":
        weights = {"relevance": 0.3, "conversion": 0.6, "freshness": 0.1}
    elif mode == "freshness_first":
        weights = {"relevance": 0.3, "conversion": 0.2, "freshness": 0.5}
    else:
        weights = {"relevance": 0.5, "conversion": 0.3, "freshness": 0.2}

    return MultiObjectiveScorer(weights=weights)
