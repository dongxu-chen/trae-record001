import pandas as pd
import numpy as np
from scipy import stats


def compute_ab_test_results(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for group in df["ab_group"].unique():
        group_df = df[df["ab_group"] == group]
        cart_df = group_df[group_df["behavior_path"].str.contains("加入购物车")]

        total = len(cart_df)
        if total == 0:
            continue

        completed = cart_df["completed"].sum()
        abandoned = total - completed
        completion_rate = completed / total
        abandonment_rate = 1 - completion_rate

        avg_cart = cart_df["cart_value"].mean()
        avg_duration = cart_df["session_duration_sec"].mean()
        avg_pages = cart_df["pages_viewed"].mean()

        reason_dist = (
            cart_df[~cart_df["completed"]]["abandonment_reason"]
            .value_counts(normalize=True)
            .to_dict()
            if abandoned > 0
            else {}
        )

        results.append(
            {
                "group": group,
                "total_sessions": total,
                "completed": completed,
                "abandoned": abandoned,
                "completion_rate": round(completion_rate, 4),
                "abandonment_rate": round(abandonment_rate, 4),
                "avg_cart_value": round(avg_cart, 2),
                "avg_session_duration": round(avg_duration, 1),
                "avg_pages_viewed": round(avg_pages, 1),
                "reason_distribution": reason_dist,
            }
        )

    return pd.DataFrame(results)


def perform_significance_test(df: pd.DataFrame, group_a: str, group_b: str, n_comparisons: int = 1) -> dict:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    group_a_data = cart_df[cart_df["ab_group"] == group_a]["completed"].astype(int)
    group_b_data = cart_df[cart_df["ab_group"] == group_b]["completed"].astype(int)

    if len(group_a_data) == 0 or len(group_b_data) == 0:
        return {"error": "Insufficient data for one or both groups"}

    n_a = len(group_a_data)
    n_b = len(group_b_data)
    p_a = group_a_data.mean()
    p_b = group_b_data.mean()

    se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)

    if se == 0:
        return {"error": "Zero standard error"}

    z_score = (p_b - p_a) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

    bonferroni_alpha = 0.05 / n_comparisons
    bonferroni_p_value = min(p_value * n_comparisons, 1.0)

    ci_low = (p_b - p_a) - 1.96 * se
    ci_high = (p_b - p_a) + 1.96 * se

    lift = ((p_b - p_a) / p_a * 100) if p_a > 0 else 0

    return {
        "group_a": group_a,
        "group_b": group_b,
        "rate_a": round(p_a, 4),
        "rate_b": round(p_b, 4),
        "difference": round(p_b - p_a, 4),
        "lift": round(lift, 2),
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 6),
        "ci_95": (round(ci_low, 4), round(ci_high, 4)),
        "significant_005": p_value < 0.05,
        "significant_001": p_value < 0.01,
        "n_a": n_a,
        "n_b": n_b,
        "n_comparisons": n_comparisons,
        "bonferroni_p_value": round(bonferroni_p_value, 6),
        "bonferroni_alpha": round(bonferroni_alpha, 6),
        "bonferroni_significant": bonferroni_p_value < 0.05,
    }


def perform_all_pairwise_tests(df: pd.DataFrame) -> list:
    groups = sorted(df["ab_group"].unique().tolist())
    n_groups = len(groups)
    n_comparisons = n_groups * (n_groups - 1) // 2

    results = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            result = perform_significance_test(df, groups[i], groups[j], n_comparisons)
            results.append(result)

    return results


def compute_ab_trend(df: pd.DataFrame, group_a: str, group_b: str) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    results = []
    for month in sorted(cart_df["month"].unique()):
        month_df = cart_df[cart_df["month"] == month]

        a_data = month_df[month_df["ab_group"] == group_a]
        b_data = month_df[month_df["ab_group"] == group_b]

        if len(a_data) == 0 or len(b_data) == 0:
            continue

        rate_a = a_data["completed"].mean()
        rate_b = b_data["completed"].mean()

        results.append(
            {
                "month": month,
                f"rate_{group_a}": round(rate_a, 4),
                f"rate_{group_b}": round(rate_b, 4),
                "difference": round(rate_b - rate_a, 4),
            }
        )

    return pd.DataFrame(results)


def compute_ab_reason_comparison(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    cross = pd.crosstab(abandoned["ab_group"], abandoned["abandonment_reason"])
    cross_pct = (cross.div(cross.sum(axis=1), axis=0) * 100).round(2)

    return cross, cross_pct


def compute_sample_size_estimate(baseline_rate: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> dict:
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    p1 = baseline_rate
    p2 = baseline_rate * (1 + mde)

    n = ((z_alpha * np.sqrt(2 * p1 * (1 - p1)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / (p2 - p1)) ** 2

    return {
        "baseline_rate": baseline_rate,
        "minimum_detectable_effect": mde,
        "alpha": alpha,
        "power": power,
        "sample_size_per_group": int(np.ceil(n)),
        "total_sample_size": int(np.ceil(n * 2)),
        "expected_rate_treatment": round(p2, 4),
    }
