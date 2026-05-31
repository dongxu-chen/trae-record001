import pandas as pd
import numpy as np


def compute_reason_attribution(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    reason_counts = abandoned["abandonment_reason"].value_counts()
    total = len(abandoned)

    result = pd.DataFrame(
        {
            "reason": reason_counts.index,
            "count": reason_counts.values,
            "percentage": (reason_counts.values / total * 100).round(2),
        }
    )

    return result


def compute_sub_reason_attribution(df: pd.DataFrame, reason: str = None) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    if reason:
        abandoned = abandoned[abandoned["abandonment_reason"] == reason]

    sub_counts = abandoned["abandonment_sub_reason"].value_counts()
    total = len(abandoned)

    if total == 0:
        return pd.DataFrame(columns=["sub_reason", "count", "percentage"])

    result = pd.DataFrame(
        {
            "sub_reason": sub_counts.index,
            "count": sub_counts.values,
            "percentage": (sub_counts.values / total * 100).round(2),
        }
    )

    return result


def compute_reason_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    cross = pd.crosstab(abandoned["user_segment"], abandoned["abandonment_reason"])
    cross_pct = (cross.div(cross.sum(axis=1), axis=0) * 100).round(2)

    return cross, cross_pct


def compute_reason_by_category(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    cross = pd.crosstab(abandoned["product_category"], abandoned["abandonment_reason"])
    cross_pct = (cross.div(cross.sum(axis=1), axis=0) * 100).round(2)

    return cross, cross_pct


def compute_survey_analysis(df: pd.DataFrame) -> dict:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    abandoned = cart_df[~cart_df["completed"]]

    surveyed = abandoned[abandoned["survey_main_reason"].notna()]
    response_rate = len(surveyed) / len(abandoned) * 100 if len(abandoned) > 0 else 0

    if len(surveyed) == 0:
        return {
            "response_rate": 0,
            "reason_distribution": pd.DataFrame(),
            "price_feel_distribution": pd.DataFrame(),
            "return_willingness": pd.DataFrame(),
            "reason_vs_behavior": pd.DataFrame(),
            "survey_vs_behavior_consistency": 0,
        }

    reason_counts = surveyed["survey_main_reason"].value_counts()
    reason_df = pd.DataFrame({
        "survey_reason": reason_counts.index,
        "count": reason_counts.values,
        "percentage": (reason_counts.values / len(surveyed) * 100).round(2),
    })

    price_counts = surveyed["survey_price_feel"].value_counts()
    price_df = pd.DataFrame({
        "price_feel": price_counts.index,
        "count": price_counts.values,
        "percentage": (price_counts.values / len(surveyed) * 100).round(2),
    })

    return_counts = surveyed["survey_return_willingness"].value_counts()
    return_df = pd.DataFrame({
        "return_willingness": return_counts.index,
        "count": return_counts.values,
        "percentage": (return_counts.values / len(surveyed) * 100).round(2),
    })

    behavior_reason_map = {
        "价格敏感": "价格太贵",
        "运费问题": "运费不合理",
        "登录门槛": "需要注册太麻烦",
        "支付障碍": "支付方式不支持",
        "比较犹豫": "还在犹豫比较",
    }

    surveyed_copy = surveyed.copy()
    surveyed_copy["mapped_behavior_reason"] = surveyed_copy["abandonment_reason"].map(behavior_reason_map)
    consistent = (surveyed_copy["survey_main_reason"] == surveyed_copy["mapped_behavior_reason"]).sum()
    consistency_rate = consistent / len(surveyed_copy) * 100

    cross = pd.crosstab(surveyed_copy["abandonment_reason"], surveyed_copy["survey_main_reason"])

    return {
        "response_rate": round(response_rate, 2),
        "reason_distribution": reason_df,
        "price_feel_distribution": price_df,
        "return_willingness": return_df,
        "reason_vs_behavior": cross,
        "survey_vs_behavior_consistency": round(consistency_rate, 2),
    }


def compute_price_sensitivity_by_user(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    user_sensitivity = (
        cart_df.groupby("user_id")
        .agg(
            price_sensitivity_score=("price_sensitivity_score", "mean"),
            total_sessions=("session_id", "count"),
            completed_rate=("completed", "mean"),
            avg_cart_value=("cart_value", "mean"),
        )
        .reset_index()
    )

    bins = [0, 0.2, 0.5, 1.0]
    labels = ["低敏感", "中敏感", "高敏感"]
    user_sensitivity["sensitivity_level"] = pd.cut(
        user_sensitivity["price_sensitivity_score"], bins=bins, labels=labels
    )

    level_summary = (
        user_sensitivity.groupby("sensitivity_level", observed=True)
        .agg(
            user_count=("user_id", "count"),
            avg_abandonment_rate=("completed_rate", lambda x: (1 - x).mean() * 100),
            avg_sensitivity_score=("price_sensitivity_score", "mean"),
            avg_cart_value=("avg_cart_value", "mean"),
        )
        .reset_index()
    )
    level_summary["avg_abandonment_rate"] = level_summary["avg_abandonment_rate"].round(2)
    level_summary["avg_sensitivity_score"] = level_summary["avg_sensitivity_score"].round(4)
    level_summary["avg_cart_value"] = level_summary["avg_cart_value"].round(2)

    return user_sensitivity, level_summary


def compute_price_sensitivity_analysis(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    bins = [0, 50, 100, 200, 500, 1000, 5000, float("inf")]
    labels = ["0-50", "50-100", "100-200", "200-500", "500-1000", "1000-5000", "5000+"]
    cart_df["price_range"] = pd.cut(cart_df["cart_value"], bins=bins, labels=labels)

    result = (
        cart_df.groupby("price_range", observed=True)
        .agg(
            total=("session_id", "count"),
            completed=("completed", "sum"),
            avg_value=("cart_value", "mean"),
        )
        .reset_index()
    )
    result["abandoned"] = result["total"] - result["completed"]
    result["abandonment_rate"] = (result["abandoned"] / result["total"] * 100).round(2)
    result["avg_value"] = result["avg_value"].round(2)

    return result


def compute_shipping_impact_analysis(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    cart_df["has_shipping_fee"] = cart_df["shipping_fee"] > 0

    result = (
        cart_df.groupby("has_shipping_fee")
        .agg(
            total=("session_id", "count"),
            completed=("completed", "sum"),
            avg_shipping=("shipping_fee", "mean"),
        )
        .reset_index()
    )
    result["abandoned"] = result["total"] - result["completed"]
    result["abandonment_rate"] = (result["abandoned"] / result["total"] * 100).round(2)
    result["avg_shipping"] = result["avg_shipping"].round(2)
    result["has_shipping_fee"] = result["has_shipping_fee"].map({True: "有运费", False: "免运费"})

    return result


def compute_login_barrier_analysis(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    def check_checkout_stage(path):
        if "去结算" not in path:
            return "未进入结算"
        elif "填写地址" not in path:
            return "结算页放弃"
        elif "选择支付" not in path:
            return "地址页放弃"
        else:
            return "支付页放弃"

    abandoned = cart_df[~cart_df["completed"]].copy()
    abandoned["checkout_stage"] = abandoned["behavior_path"].apply(check_checkout_stage)

    stage_counts = abandoned["checkout_stage"].value_counts()
    total = len(abandoned)

    result = pd.DataFrame(
        {
            "stage": stage_counts.index,
            "count": stage_counts.values,
            "percentage": (stage_counts.values / total * 100).round(2),
        }
    )

    login_barrier_stages = ["未进入结算", "结算页放弃"]
    login_barrier_pct = result[result["stage"].isin(login_barrier_stages)]["percentage"].sum()

    return result, login_barrier_pct


def compute_attribution_summary(df: pd.DataFrame) -> dict:
    reason_attr = compute_reason_attribution(df)
    price_analysis = compute_price_sensitivity_analysis(df)
    shipping_analysis = compute_shipping_impact_analysis(df)
    checkout_analysis, login_pct = compute_login_barrier_analysis(df)

    return {
        "reason_attribution": reason_attr,
        "price_sensitivity": price_analysis,
        "shipping_impact": shipping_analysis,
        "checkout_stage_analysis": checkout_analysis,
        "login_barrier_pct": login_pct,
    }


def compute_competitor_impact(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    result = cart_df.groupby("has_lower_competitor").agg(
        total=("session_id", "count"),
        completed=("completed", "sum"),
        avg_cart_value=("cart_value", "mean"),
        avg_price_diff=("price_diff_vs_lowest", "mean"),
    ).reset_index()

    result["abandoned"] = result["total"] - result["completed"]
    result["abandonment_rate"] = (result["abandoned"] / result["total"] * 100).round(2)
    result["avg_cart_value"] = result["avg_cart_value"].round(2)
    result["avg_price_diff"] = result["avg_price_diff"].round(2)
    result["has_lower_competitor"] = result["has_lower_competitor"].map({True: "竞品更低价", False: "本平台最低价"})

    return result


def compute_competitor_by_category(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    result = cart_df.groupby("product_category").agg(
        total=("session_id", "count"),
        has_lower_pct=("has_lower_competitor", "mean"),
        avg_price_diff_pct=("price_diff_pct_vs_lowest", "mean"),
        completed_rate=("completed", "mean"),
        avg_sensitivity=("price_sensitivity_score", "mean"),
    ).reset_index()

    result["has_lower_pct"] = (result["has_lower_pct"] * 100).round(2)
    result["avg_price_diff_pct"] = result["avg_price_diff_pct"].round(2)
    result["abandonment_rate"] = ((1 - result["completed_rate"]) * 100).round(2)
    result["avg_sensitivity"] = result["avg_sensitivity"].round(4)

    return result.sort_values("abandonment_rate", ascending=False)


def compute_price_diff_abandonment(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    bins = [-float("inf"), -5, 0, 5, 10, 20, float("inf")]
    labels = ["竞品便宜>20%", "竞品便宜5-20%", "价格相近(±5%)", "本平台贵5-10%", "本平台贵10-20%", "本平台贵>20%"]
    cart_df["price_diff_bucket"] = pd.cut(cart_df["price_diff_pct_vs_lowest"], bins=bins, labels=labels)

    result = cart_df.groupby("price_diff_bucket", observed=True).agg(
        total=("session_id", "count"),
        completed=("completed", "sum"),
        avg_diff_pct=("price_diff_pct_vs_lowest", "mean"),
    ).reset_index()

    result["abandoned"] = result["total"] - result["completed"]
    result["abandonment_rate"] = (result["abandoned"] / result["total"] * 100).round(2)
    result["avg_diff_pct"] = result["avg_diff_pct"].round(2)

    return result


def compute_competitor_by_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    sens_bins = [0, 0.2, 0.5, 1.01]
    sens_labels = ["低敏感", "中敏感", "高敏感"]
    cart_df["sensitivity_level"] = pd.cut(cart_df["price_sensitivity_score"], bins=sens_bins, labels=sens_labels)

    result = cart_df.groupby(["sensitivity_level", "has_lower_competitor"], observed=True).agg(
        total=("session_id", "count"),
        completed=("completed", "mean"),
    ).reset_index()

    result["abandonment_rate"] = ((1 - result["completed"]) * 100).round(2)
    result["has_lower_competitor"] = result["has_lower_competitor"].map({True: "竞品更低价", False: "本平台最低"})

    return result
