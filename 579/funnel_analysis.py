import pandas as pd
import numpy as np
from collections import Counter


FUNNEL_STAGES = ["浏览商品", "加入购物车", "查看购物车", "去结算", "填写地址", "选择支付", "确认支付", "支付成功"]


def compute_funnel(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    stage_counts = {}
    for stage in FUNNEL_STAGES:
        count = df["behavior_path"].apply(lambda p: stage in p).sum()
        stage_counts[stage] = count

    funnel_df = pd.DataFrame(
        {"stage": list(stage_counts.keys()), "count": list(stage_counts.values())}
    )
    funnel_df["rate"] = (funnel_df["count"] / total * 100).round(2)
    funnel_df["drop_off"] = funnel_df["count"].diff().fillna(0).astype(int) * -1
    funnel_df["drop_off_rate"] = (
        (funnel_df["drop_off"] / funnel_df["count"].shift(1) * 100)
        .fillna(0)
        .round(2)
    )
    funnel_df["conversion_from_prev"] = (
        (funnel_df["count"] / funnel_df["count"].shift(1) * 100).fillna(100).round(2)
    )

    return funnel_df


def compute_funnel_by_segment(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for segment in df["user_segment"].unique():
        seg_df = df[df["user_segment"] == segment]
        funnel = compute_funnel(seg_df)
        funnel["segment"] = segment
        results.append(funnel)
    return pd.concat(results, ignore_index=True)


def compute_funnel_by_category(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for cat in df["product_category"].unique():
        cat_df = df[df["product_category"] == cat]
        funnel = compute_funnel(cat_df)
        funnel["category"] = cat
        results.append(funnel)
    return pd.concat(results, ignore_index=True)


def compute_funnel_by_device(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for device in df["device"].unique():
        dev_df = df[df["device"] == device]
        funnel = compute_funnel(dev_df)
        funnel["device"] = device
        results.append(funnel)
    return pd.concat(results, ignore_index=True)


def compute_overall_abandonment_rate(df: pd.DataFrame) -> float:
    cart_users = df[df["behavior_path"].str.contains("加入购物车")]
    if len(cart_users) == 0:
        return 0.0
    abandoned = cart_users[~cart_users["completed"]]
    return round(len(abandoned) / len(cart_users) * 100, 2)


def compute_stage_drop_off_analysis(df: pd.DataFrame) -> pd.DataFrame:
    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()
    abandoned = cart_df[~cart_df["completed"]]

    last_events = abandoned["last_event"].value_counts()
    total_abandoned = len(abandoned)

    result = pd.DataFrame(
        {
            "last_event": last_events.index,
            "count": last_events.values,
            "percentage": (last_events.values / total_abandoned * 100).round(2),
        }
    )

    return result


def compute_cart_abandonment_funnel(df: pd.DataFrame) -> pd.DataFrame:
    cart_stages = ["加入购物车", "查看购物车", "去结算", "填写地址", "选择支付", "确认支付", "支付成功"]
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    total = len(cart_df)

    stage_counts = {}
    for stage in cart_stages:
        count = cart_df["behavior_path"].apply(lambda p: stage in p).sum()
        stage_counts[stage] = count

    funnel_df = pd.DataFrame(
        {"stage": list(stage_counts.keys()), "count": list(stage_counts.values())}
    )
    funnel_df["rate"] = (funnel_df["count"] / total * 100).round(2)
    funnel_df["drop_off"] = funnel_df["count"].diff().fillna(0).astype(int) * -1
    funnel_df["drop_off_rate"] = (
        (funnel_df["drop_off"] / funnel_df["count"].shift(1) * 100)
        .fillna(0)
        .round(2)
    )

    return funnel_df
