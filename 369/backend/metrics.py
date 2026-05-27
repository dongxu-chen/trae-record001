import numpy as np
from typing import List, Dict, Tuple, Optional
from schemas import SearchResult, EvaluationMetrics, ConfusionMatrix


def calculate_dcg(relevance_scores: List[int], k: Optional[int] = None) -> float:
    if k:
        relevance_scores = relevance_scores[:k]
    dcg = 0.0
    for i, rel in enumerate(relevance_scores):
        dcg += rel / np.log2(i + 2)
    return dcg


def calculate_ndcg(relevance_scores: List[int], k: Optional[int] = None) -> float:
    dcg = calculate_dcg(relevance_scores, k)
    ideal_scores = sorted(relevance_scores, reverse=True)
    idcg = calculate_dcg(ideal_scores, k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def calculate_recall_at_k(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str],
    k: int
) -> float:
    if not relevant_docs:
        return 0.0
    retrieved_k = [r.doc_id for r in retrieved_docs[:k]]
    relevant_retrieved = len(set(retrieved_k) & set(relevant_docs))
    return relevant_retrieved / len(relevant_docs)


def calculate_precision_at_k(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str],
    k: int
) -> float:
    if k == 0:
        return 0.0
    retrieved_k = [r.doc_id for r in retrieved_docs[:k]]
    relevant_retrieved = len(set(retrieved_k) & set(relevant_docs))
    return relevant_retrieved / k


def calculate_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def calculate_hit_rate(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str],
    k: int
) -> float:
    if not relevant_docs:
        return 0.0
    retrieved_k = [r.doc_id for r in retrieved_docs[:k]]
    hit = any(doc in relevant_docs for doc in retrieved_k)
    return 1.0 if hit else 0.0


def calculate_mrr(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str]
) -> float:
    for i, result in enumerate(retrieved_docs):
        if result.doc_id in relevant_docs:
            return 1.0 / (i + 1)
    return 0.0


def calculate_map(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str]
) -> float:
    if not relevant_docs:
        return 0.0
    avg_precisions = []
    relevant_retrieved = 0
    for i, result in enumerate(retrieved_docs):
        if result.doc_id in relevant_docs:
            relevant_retrieved += 1
            precision_at_i = relevant_retrieved / (i + 1)
            avg_precisions.append(precision_at_i)
    if not avg_precisions:
        return 0.0
    return sum(avg_precisions) / len(relevant_docs)


def calculate_confusion_matrix(
    retrieved_docs: List[SearchResult],
    relevant_docs: List[str],
    all_docs_count: int,
    k: int
) -> ConfusionMatrix:
    retrieved_set = set([r.doc_id for r in retrieved_docs[:k]])
    relevant_set = set(relevant_docs)

    tp = len(retrieved_set & relevant_set)
    fp = len(retrieved_set - relevant_set)
    fn = len(relevant_set - retrieved_set)
    tn = max(0, all_docs_count - tp - fp - fn)

    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = calculate_f1(precision, recall)
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return ConfusionMatrix(
        tp=tp, fp=fp, fn=fn, tn=tn,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        specificity=specificity
    )


def evaluate_search_results(
    retrieved_docs: List[SearchResult],
    relevant_docs_with_relevance: Dict[str, int],
    k: int
) -> EvaluationMetrics:
    relevant_docs = [doc_id for doc_id, rel in relevant_docs_with_relevance.items() if rel > 0]

    recall = calculate_recall_at_k(retrieved_docs, relevant_docs, k)
    precision = calculate_precision_at_k(retrieved_docs, relevant_docs, k)
    f1 = calculate_f1(precision, recall)
    hit_rate = calculate_hit_rate(retrieved_docs, relevant_docs, k)
    mrr = calculate_mrr(retrieved_docs, relevant_docs)
    map_score = calculate_map(retrieved_docs, relevant_docs)

    relevance_scores = []
    for result in retrieved_docs[:k]:
        relevance_scores.append(relevant_docs_with_relevance.get(result.doc_id, 0))
    ndcg = calculate_ndcg(relevance_scores, k)

    avg_precision = 0.0
    if relevant_docs:
        precisions = []
        relevant_count = 0
        for i, result in enumerate(retrieved_docs[:k]):
            if result.doc_id in relevant_docs:
                relevant_count += 1
                precisions.append(relevant_count / (i + 1))
        avg_precision = sum(precisions) / len(relevant_docs) if precisions else 0.0

    return EvaluationMetrics(
        recall_at_k=recall,
        precision_at_k=precision,
        f1_at_k=f1,
        hit_rate=hit_rate,
        mrr=mrr,
        ndcg_at_k=ndcg,
        map_at_k=map_score,
        average_precision=avg_precision
    )


def aggregate_metrics(metrics_list: List[EvaluationMetrics]) -> Dict[str, float]:
    if not metrics_list:
        return {}
    return {
        "avg_recall": np.mean([m.recall_at_k for m in metrics_list]),
        "avg_precision": np.mean([m.precision_at_k for m in metrics_list]),
        "avg_f1": np.mean([m.f1_at_k for m in metrics_list]),
        "avg_hit_rate": np.mean([m.hit_rate for m in metrics_list]),
        "avg_mrr": np.mean([m.mrr for m in metrics_list]),
        "avg_ndcg": np.mean([m.ndcg_at_k for m in metrics_list]),
        "avg_map": np.mean([m.map_at_k for m in metrics_list]),
    }
