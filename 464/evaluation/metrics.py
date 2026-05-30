import math
import numpy as np


def dcg_at_k(relevances, k):
    relevances = np.array(relevances, dtype=np.float64)[:k]
    if len(relevances) == 0:
        return 0.0
    gains = (2.0 ** relevances - 1.0)
    discounts = np.log2(np.arange(len(relevances)) + 2.0)
    return float(np.sum(gains / discounts))


def ndcg_at_k(relevances, k):
    dcg = dcg_at_k(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal_relevances, k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def average_precision(relevances):
    relevances = np.array(relevances, dtype=np.float64)
    if len(relevances) == 0:
        return 0.0
    num_relevant = np.sum(relevances > 0)
    if num_relevant == 0:
        return 0.0
    ap = 0.0
    num_retrieved = 0
    for i, rel in enumerate(relevances):
        if rel > 0:
            num_retrieved += 1
            precision_at_i = num_retrieved / (i + 1)
            ap += precision_at_i
    return ap / num_relevant


def mean_average_precision(all_relevances):
    aps = [average_precision(rels) for rels in all_relevances]
    return float(np.mean(aps)) if aps else 0.0


def mean_ndcg_at_k(all_relevances, k):
    ndcgs = [ndcg_at_k(rels, k) for rels in all_relevances]
    return float(np.mean(ndcgs)) if ndcgs else 0.0


def classify_query_type(query, query_frequency=None, freq_threshold=0.5):
    if query_frequency is not None:
        freq = query_frequency.get(query, 0)
        median_freq = np.median(list(query_frequency.values())) if query_frequency else 1.0
        return "popular" if freq >= median_freq * freq_threshold else "longtail"

    word_count = len(query.split())
    char_length = len(query)
    if char_length <= 4 and word_count <= 2:
        return "popular"
    else:
        return "longtail"


def get_query_types(queries, query_frequency=None):
    return [classify_query_type(q, query_frequency) for q in queries]


def evaluate_ranking_by_group(predictions, labels, query_ids, query_groups, k_values=None):
    if k_values is None:
        k_values = [1, 3, 5, 10]

    predictions = np.array(predictions, dtype=np.float64)
    labels = np.array(labels, dtype=np.float64)
    query_ids = np.array(query_ids)
    query_groups = np.array(query_groups)

    unique_groups = np.unique(query_groups)
    group_results = {}

    for group in unique_groups:
        group_mask = np.isin(query_ids, np.unique(query_ids[query_groups == group]))
        group_preds = predictions[group_mask]
        group_labels = labels[group_mask]
        group_qids = query_ids[group_mask]

        results = evaluate_ranking(group_preds, group_labels, group_qids, k_values)
        group_results[group] = {
            "metrics": results,
            "num_queries": len(np.unique(group_qids)),
            "num_samples": len(group_preds),
        }

    overall = evaluate_ranking(predictions, labels, query_ids, k_values)
    group_results["overall"] = {
        "metrics": overall,
        "num_queries": len(np.unique(query_ids)),
        "num_samples": len(predictions),
    }

    return group_results


def evaluate_ranking(predictions, labels, query_ids, k_values=None):
    if k_values is None:
        k_values = [1, 3, 5, 10]

    predictions = np.array(predictions, dtype=np.float64)
    labels = np.array(labels, dtype=np.float64)
    query_ids = np.array(query_ids)

    unique_queries = np.unique(query_ids)
    all_relevances = []
    ndcg_results = {k: [] for k in k_values}

    for qid in unique_queries:
        mask = query_ids == qid
        q_preds = predictions[mask]
        q_labels = labels[mask]

        sorted_indices = np.argsort(-q_preds)
        sorted_labels = q_labels[sorted_indices]

        all_relevances.append(sorted_labels)

        for k in k_values:
            ndcg_results[k].append(ndcg_at_k(sorted_labels, k))

    results = {
        "MAP": mean_average_precision(all_relevances),
    }
    for k in k_values:
        results[f"NDCG@{k}"] = float(np.mean(ndcg_results[k]))

    return results


def print_group_evaluation_results(group_results, k_values=None):
    if k_values is None:
        k_values = [1, 3, 5, 10]

    print("\n" + "=" * 70)
    print("  Fine-Grained Search Relevance Evaluation Results")
    print("=" * 70)

    groups = [g for g in group_results.keys() if g != "overall"]
    if "overall" in group_results:
        groups.append("overall")

    header = f"  {'Group':<15} {'Count':<8}"
    header += f" {'MAP':<8}"
    for k in k_values:
        header += f" NDCG@{k:<5}"
    print(header)
    print("  " + "-" * 68)

    for group in groups:
        data = group_results[group]
        metrics = data["metrics"]
        count = data["num_queries"]

        row = f"  {group:<15} {count:<8}"
        row += f" {metrics.get('MAP', 0):<8.4f}"
        for k in k_values:
            row += f" {metrics.get(f'NDCG@{k}', 0):<8.4f}"
        print(row)

    print("=" * 70)


def print_evaluation_results(results):
    print("\n" + "=" * 50)
    print("  Search Relevance Ranking Evaluation Results")
    print("=" * 50)
    for metric, value in results.items():
        print(f"  {metric:12s}: {value:.4f}")
    print("=" * 50)
