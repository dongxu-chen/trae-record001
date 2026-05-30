import random
import numpy as np


def compute_label_confidence(query, product, label_fn, num_samples=3, **kwargs):
    labels = []
    for _ in range(num_samples):
        label = label_fn(query, [product], **kwargs)[0]
        labels.append(label)
    label_counts = {}
    for l in labels:
        label_counts[l] = label_counts.get(l, 0) + 1
    majority_label = max(label_counts, key=label_counts.get)
    agreement = label_counts[majority_label] / len(labels)
    return majority_label, agreement, labels


def check_data_consistency(queries, products, label_fn, consistency_threshold=0.66, num_annotations=3, **kwargs):
    consistent_labels = []
    inconsistent_samples = []
    relabeled_samples = []

    for q_idx, query in enumerate(queries):
        for p_idx, product in enumerate(products):
            majority_label, agreement, all_labels = compute_label_confidence(
                query, product, label_fn, num_samples=num_annotations, **kwargs
            )

            if agreement >= consistency_threshold:
                consistent_labels.append({
                    "query_idx": q_idx,
                    "product_idx": p_idx,
                    "label": majority_label,
                    "agreement": agreement,
                    "all_labels": all_labels,
                })
            else:
                inconsistent_samples.append({
                    "query_idx": q_idx,
                    "product_idx": p_idx,
                    "current_labels": all_labels,
                    "agreement": agreement,
                })

    return consistent_labels, inconsistent_samples


def relabel_inconsistent_samples(inconsistent_samples, queries, products, label_fn,
                                  max_relabel_attempts=5, consistency_threshold=0.66, **kwargs):
    relabeled = []
    still_inconsistent = []

    for sample in inconsistent_samples:
        q_idx = sample["query_idx"]
        p_idx = sample["product_idx"]
        query = queries[q_idx]
        product = products[p_idx]

        best_agreement = sample["agreement"]
        best_label = None
        best_all_labels = None

        for attempt in range(max_relabel_attempts):
            majority_label, agreement, all_labels = compute_label_confidence(
                query, product, label_fn, num_samples=3, **kwargs
            )

            if agreement > best_agreement:
                best_agreement = agreement
                best_label = majority_label
                best_all_labels = all_labels

            if best_agreement >= consistency_threshold:
                break

        if best_agreement >= consistency_threshold:
            relabeled.append({
                "query_idx": q_idx,
                "product_idx": p_idx,
                "label": best_label,
                "agreement": best_agreement,
                "all_labels": best_all_labels,
                "attempts": attempt + 1,
            })
        else:
            still_inconsistent.append({
                "query_idx": q_idx,
                "product_idx": p_idx,
                "final_agreement": best_agreement,
                "attempts": max_relabel_attempts,
            })

    return relabeled, still_inconsistent


def build_consistent_dataset(queries, products, label_fn,
                              consistency_threshold=0.66,
                              num_initial_annotations=3,
                              max_relabel_attempts=5,
                              drop_inconsistent=True,
                              **kwargs):
    all_product_pairs = []
    for q_idx, query in enumerate(queries):
        num_candidates = random.randint(8, 20)
        candidate_indices = random.sample(range(len(products)), min(num_candidates, len(products)))
        for p_idx in candidate_indices:
            all_product_pairs.append((q_idx, p_idx))

    pair_labels = []
    inconsistent_pairs = []

    for q_idx, p_idx in all_product_pairs:
        query = queries[q_idx]
        product = products[p_idx]
        majority_label, agreement, all_labels = compute_label_confidence(
            query, product, label_fn, num_samples=num_initial_annotations, **kwargs
        )

        if agreement >= consistency_threshold:
            pair_labels.append({
                "query_idx": q_idx,
                "product_idx": p_idx,
                "label": majority_label,
                "agreement": agreement,
            })
        else:
            inconsistent_pairs.append((q_idx, p_idx, all_labels, agreement))

    relabeled = []
    still_inconsistent = []

    for q_idx, p_idx, init_labels, init_agree in inconsistent_pairs:
        query = queries[q_idx]
        product = products[p_idx]

        best_agreement = init_agree
        best_label = None

        for attempt in range(max_relabel_attempts):
            majority_label, agreement, _ = compute_label_confidence(
                query, product, label_fn, num_samples=3, **kwargs
            )

            if agreement > best_agreement:
                best_agreement = agreement
                best_label = majority_label

            if best_agreement >= consistency_threshold:
                break

        if best_agreement >= consistency_threshold:
            relabeled.append({
                "query_idx": q_idx,
                "product_idx": p_idx,
                "label": best_label,
                "agreement": best_agreement,
                "relabeled": True,
            })
        elif not drop_inconsistent:
            still_inconsistent.append({
                "query_idx": q_idx,
                "product_idx": p_idx,
                "label": best_label or init_labels[0],
                "agreement": best_agreement,
                "low_quality": True,
            })

    all_labels = pair_labels + relabeled + still_inconsistent

    grouped = {}
    for item in all_labels:
        q_idx = item["query_idx"]
        if q_idx not in grouped:
            grouped[q_idx] = []
        grouped[q_idx].append(item)

    features_by_query = []
    labels_by_query = []
    groups = []

    for q_idx in sorted(grouped.keys()):
        items = grouped[q_idx]
        q_labels = [item["label"] for item in items]
        q_p_indices = [item["product_idx"] for item in items]

        features_by_query.append((q_idx, q_p_indices))
        labels_by_query.append(q_labels)
        groups.append(len(items))

    stats = {
        "total_pairs": len(all_product_pairs),
        "consistent_initial": len(pair_labels),
        "relabeled_success": len(relabeled),
        "still_inconsistent": len(still_inconsistent),
        "avg_agreement": np.mean([item["agreement"] for item in all_labels]),
    }

    return features_by_query, labels_by_query, groups, stats


def print_consistency_stats(stats):
    print("\n  Annotation Consistency Statistics:")
    print(f"    Total query-product pairs     : {stats['total_pairs']}")
    print(f"    Consistent (initial)          : {stats['consistent_initial']}")
    print(f"    Relabeled successfully        : {stats['relabeled_success']}")
    print(f"    Still inconsistent (dropped)  : {stats['still_inconsistent']}")
    print(f"    Average agreement             : {stats['avg_agreement']:.4f}")
