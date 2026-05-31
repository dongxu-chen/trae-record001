import pandas as pd
import numpy as np


def compute_intervention_summary(df: pd.DataFrame) -> dict:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    abandoned = cart_df[~cart_df["completed"]]

    total_abandoned = len(abandoned)
    triggered = abandoned[abandoned["intervention_triggered"]]
    accepted = triggered[triggered["intervention_accepted"]]
    converted = triggered[triggered["intervention_converted"]]

    trigger_rate = len(triggered) / total_abandoned * 100 if total_abandoned > 0 else 0
    accept_rate = len(accepted) / len(triggered) * 100 if len(triggered) > 0 else 0
    convert_rate = len(converted) / len(triggered) * 100 if len(triggered) > 0 else 0
    overall_recovery = len(converted) / total_abandoned * 100 if total_abandoned > 0 else 0

    return {
        "total_abandoned": total_abandoned,
        "intervention_triggered_count": len(triggered),
        "intervention_accepted_count": len(accepted),
        "intervention_converted_count": len(converted),
        "trigger_rate": round(trigger_rate, 2),
        "accept_rate": round(accept_rate, 2),
        "convert_rate": round(convert_rate, 2),
        "overall_recovery_rate": round(overall_recovery, 2),
    }


def compute_intervention_by_type(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    triggered = cart_df[cart_df["intervention_triggered"] & ~cart_df["completed"]].copy()

    if len(triggered) == 0:
        return pd.DataFrame()

    triggered["intervention_accepted"] = triggered["intervention_accepted"].astype(int)
    triggered["intervention_converted"] = triggered["intervention_converted"].astype(int)

    type_stats = triggered.groupby("intervention_type").agg(
        triggered_count=("session_id", "count"),
        accepted_count=("intervention_accepted", "sum"),
        converted_count=("intervention_converted", "sum"),
        avg_timing=("intervention_timing_sec", "mean"),
        avg_cart_value=("cart_value", "mean"),
    ).reset_index()

    type_stats["accept_rate"] = (type_stats["accepted_count"] / type_stats["triggered_count"] * 100).round(2)
    type_stats["convert_rate"] = (type_stats["converted_count"] / type_stats["triggered_count"] * 100).round(2)
    type_stats["avg_timing"] = type_stats["avg_timing"].round(1)
    type_stats["avg_cart_value"] = type_stats["avg_cart_value"].round(2)

    return type_stats.sort_values("convert_rate", ascending=False)


def compute_intervention_by_reason(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    triggered = cart_df[cart_df["intervention_triggered"] & ~cart_df["completed"]].copy()

    if len(triggered) == 0:
        return pd.DataFrame()

    triggered["intervention_accepted"] = triggered["intervention_accepted"].astype(int)
    triggered["intervention_converted"] = triggered["intervention_converted"].astype(int)

    reason_stats = triggered.groupby("abandonment_reason").agg(
        triggered_count=("session_id", "count"),
        accepted_count=("intervention_accepted", "sum"),
        converted_count=("intervention_converted", "sum"),
    ).reset_index()

    reason_stats["accept_rate"] = (reason_stats["accepted_count"] / reason_stats["triggered_count"] * 100).round(2)
    reason_stats["convert_rate"] = (reason_stats["converted_count"] / reason_stats["triggered_count"] * 100).round(2)

    return reason_stats.sort_values("convert_rate", ascending=False)


def compute_intervention_by_timing(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    triggered = cart_df[cart_df["intervention_triggered"] & ~cart_df["completed"]].copy()

    if len(triggered) == 0:
        return pd.DataFrame()

    triggered["intervention_accepted"] = triggered["intervention_accepted"].astype(int)
    triggered["intervention_converted"] = triggered["intervention_converted"].astype(int)

    bins = [0, 5, 10, 15, 20, 30]
    labels = ["0-5秒", "5-10秒", "10-15秒", "15-20秒", "20-30秒"]
    triggered["timing_bucket"] = pd.cut(triggered["intervention_timing_sec"], bins=bins, labels=labels)

    timing_stats = triggered.groupby("timing_bucket", observed=True).agg(
        count=("session_id", "count"),
        accepted=("intervention_accepted", "sum"),
        converted=("intervention_converted", "sum"),
    ).reset_index()

    timing_stats["accept_rate"] = (timing_stats["accepted"] / timing_stats["count"] * 100).round(2)
    timing_stats["convert_rate"] = (timing_stats["converted"] / timing_stats["count"] * 100).round(2)

    return timing_stats


def compute_intervention_timeline(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    triggered = cart_df[cart_df["intervention_triggered"] & ~cart_df["completed"]].copy()

    if len(triggered) == 0:
        return pd.DataFrame()

    triggered["intervention_accepted"] = triggered["intervention_accepted"].astype(int)
    triggered["intervention_converted"] = triggered["intervention_converted"].astype(int)

    monthly = triggered.groupby("month").agg(
        triggered_count=("session_id", "count"),
        accepted_count=("intervention_accepted", "sum"),
        converted_count=("intervention_converted", "sum"),
    ).reset_index()

    monthly["accept_rate"] = (monthly["accepted_count"] / monthly["triggered_count"] * 100).round(2)
    monthly["convert_rate"] = (monthly["converted_count"] / monthly["triggered_count"] * 100).round(2)

    return monthly


def simulate_realtime_intervention(df: pd.DataFrame, risk_threshold: float = 0.6) -> dict:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    high_risk = cart_df[
        (cart_df["hesitation_score"] >= 3)
        & (cart_df["price_sensitivity_score"] > 0.3)
        & (~cart_df["completed"])
    ]

    total_high_risk = len(high_risk)

    intervention_logic = {
        "价格敏感 + 竞品更低价": len(high_risk[high_risk["has_lower_competitor"]]),
        "价格敏感 + 高客单价": len(high_risk[(high_risk["cart_value"] > 500) & (high_risk["price_sensitivity_score"] > 0.5)]),
        "运费阻力 + 价格敏感": len(high_risk[(high_risk["shipping_fee"] > 0) & (high_risk["cart_value"] < 99)]),
        "犹豫不决 + 多次离开": len(high_risk[(high_risk["mouse_leave_count"] > 2) & (high_risk["hesitation_score"] >= 5)]),
    }

    optimal_timing = {
        "0-5秒（即时）": "适合：鼠标离开页面瞬间、标签页切换",
        "5-10秒（快速）": "适合：购物车页面停留超时、价格查看返回",
        "10-15秒（适中）": "适合：反复查看购物车、修改数量后犹豫",
        "15-30秒（延迟）": "适合：深度对比用户，给足思考时间后推送",
    }

    return {
        "total_high_risk_sessions": total_high_risk,
        "intervention_breakdown": intervention_logic,
        "optimal_timing_guidance": optimal_timing,
        "risk_threshold_used": risk_threshold,
    }
