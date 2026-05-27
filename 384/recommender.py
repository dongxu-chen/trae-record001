from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


FEATURE_LABELS: Dict[str, str] = {
    "start_hour": "开播时段",
    "weekday": "星期",
    "is_holiday": "节假日",
    "platform_activity": "平台活动",
    "duration_hours": "直播时长",
    "avg_viewers": "平均观看人数",
    "engagement_rate": "互动率",
    "gift_income": "礼物收入",
    "peak_viewers": "峰值观看人数",
}


@dataclass
class Recommendation:
    optimal_hour: int
    best_weekdays: List[str]
    recommended_duration: float
    content_direction: str
    holiday_advice: str
    activity_advice: str
    key_drivers: List[str]
    reason: str


@dataclass
class CompetitorGap:
    metric: str
    our_value: float
    competitor_avg: float
    gap: float
    pct_gap: float
    advice: str


@dataclass
class CompetitorReport:
    gaps: List[CompetitorGap]
    same_category_competitors: List[str]
    top_benchmark: str
    summary: str


def _feature_importance_to_drivers(
    feature_importance: Optional[List[float]],
    feature_columns: List[str],
    top_k: int = 5,
) -> List[str]:
    if not feature_importance:
        return []
    pairs = list(zip(feature_columns, feature_importance))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return [FEATURE_LABELS.get(col, col) for col, _ in pairs[:top_k]]


def _holiday_analysis(df: pd.DataFrame) -> str:
    if "is_holiday" not in df.columns:
        return ""
    holiday_df = df[df["is_holiday"] == 1]
    normal_df = df[df["is_holiday"] == 0]
    if len(holiday_df) == 0 or len(normal_df) == 0:
        return "节假日样本不足，建议在后续节假日多做直播积累数据。"
    h_peak = holiday_df["peak_viewers"].mean()
    n_peak = normal_df["peak_viewers"].mean()
    h_income = holiday_df["gift_income"].mean()
    n_income = normal_df["gift_income"].mean()
    peak_pct = (h_peak - n_peak) / max(n_peak, 1) * 100
    income_pct = (h_income - n_income) / max(n_income, 1) * 100
    if peak_pct > 10 and income_pct > 10:
        return f"节假日表现显著优于平日（峰值+{peak_pct:.1f}%，收入+{income_pct:.1f}%），建议在节假日延长直播时长并加大互动投入。"
    elif peak_pct < -10:
        return f"节假日峰值反而下降（{peak_pct:.1f}%），可能观众有外出安排，建议调整为深夜档或缩短时长。"
    else:
        return f"节假日与平日差异不大（峰值{peak_pct:+.1f}%，收入{income_pct:+.1f}%），可维持常规策略。"


def _activity_analysis(df: pd.DataFrame) -> str:
    if "platform_activity" not in df.columns:
        return ""
    activity_vals = df["platform_activity"].unique()
    if len(activity_vals) <= 1:
        return "平台活动样本不足，建议在活动日多开播以评估影响。"
    high_activity = df[df["platform_activity"] >= 0.5]
    low_activity = df[df["platform_activity"] < 0.5]
    if len(high_activity) == 0 or len(low_activity) == 0:
        return "活动日数据有限，建议在平台大促（如 618、双11）期间重点运营。"
    h_income = high_activity["gift_income"].mean()
    l_income = low_activity["gift_income"].mean()
    pct = (h_income - l_income) / max(l_income, 1) * 100
    if pct > 15:
        return f"平台活动日收入显著提升（+{pct:.1f}%），建议在大促期间配合平台活动做主题直播。"
    elif pct < -10:
        return f"平台活动日收入反而下降（{pct:.1f}%），可能受其他主播挤压，建议错开活动高峰或做差异化内容。"
    else:
        return f"平台活动日与平日差异不大（{pct:+.1f}%），可根据资源灵活安排。"


def generate_recommendations(
    df: pd.DataFrame,
    feature_importance: Optional[List[float]] = None,
    feature_columns: Optional[List[str]] = None,
) -> Recommendation:
    work_df = df.copy()
    work_df["hour_bucket"] = pd.cut(
        work_df["start_hour"],
        bins=[-1, 6, 12, 16, 20, 24],
        labels=["凌晨", "上午", "下午", "黄金档", "深夜"],
        include_lowest=True,
    )
    hour_stats = (
        work_df.groupby("start_hour", observed=True)[["peak_viewers", "gift_income", "engagement_rate"]]
        .mean()
        .sort_values("gift_income", ascending=False)
    )
    if hour_stats.empty:
        return Recommendation(20, ["周五", "周六", "周日"], 3.0, "综合内容",
                              "节假日数据不足", "平台活动数据不足", [],
                              "历史数据不足，使用默认建议。")
    optimal_hour = int(hour_stats.index[0])

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    work_df["weekday_name"] = work_df["weekday"].map(lambda x: weekday_names[int(x) % 7])
    weekday_stats = (
        work_df.groupby("weekday_name", observed=True)[["peak_viewers", "gift_income"]]
        .mean()
        .sort_values("gift_income", ascending=False)
    )
    best_weekdays = list(weekday_stats.head(3).index)

    recommended_duration = float(np.clip(work_df["duration_hours"].mean(), 2.0, 5.0))

    cat_stats = (
        work_df.groupby("category", observed=True)[["peak_viewers", "gift_income", "engagement_rate"]]
        .mean()
        .sort_values("gift_income", ascending=False)
    )
    best_category = str(cat_stats.index[0]) if not cat_stats.empty else "综合"

    eng = float(work_df["engagement_rate"].mean())
    income = float(work_df["gift_income"].mean())
    if eng > 0.08 and income > work_df["gift_income"].median():
        content_direction = f"保持当前 {best_category} 方向，增加互动环节（抽奖/连麦），巩固高互动率。"
    elif eng < 0.05:
        content_direction = f"建议向 {best_category} 方向倾斜，提升话题性与互动设计（问答、点歌）。"
    else:
        content_direction = f"以 {best_category} 为主线，结合观众偏好尝试新形式，保持内容新鲜感。"

    holiday_advice = _holiday_analysis(work_df)
    activity_advice = _activity_analysis(work_df)

    key_drivers = _feature_importance_to_drivers(
        feature_importance, feature_columns or []
    )

    reason_parts = [
        f"基于历史数据统计，最佳开播时段为 {optimal_hour}:00，",
        f"表现最好的星期为 {', '.join(best_weekdays)}，",
        f"平均有效时长约 {recommended_duration:.1f} 小时。",
    ]
    if key_drivers:
        reason_parts.append(f"模型识别的关键驱动因素：{', '.join(key_drivers)}。")
    reason = " ".join(reason_parts)

    return Recommendation(
        optimal_hour=optimal_hour,
        best_weekdays=best_weekdays,
        recommended_duration=recommended_duration,
        content_direction=content_direction,
        holiday_advice=holiday_advice,
        activity_advice=activity_advice,
        key_drivers=key_drivers,
        reason=reason,
    )


def generate_competitor_analysis(
    our_df: pd.DataFrame,
    competitor_df: pd.DataFrame,
    our_predicted_peak: Optional[float] = None,
    our_predicted_income: Optional[float] = None,
    our_predicted_engagement: Optional[float] = None,
) -> CompetitorReport:
    if competitor_df.empty:
        return CompetitorReport([], [], "暂无竞品数据", "竞品数据为空，无法进行对比分析。")

    our_avg_peak = our_predicted_peak if our_predicted_peak is not None else float(our_df["peak_viewers"].mean())
    our_avg_income = our_predicted_income if our_predicted_income is not None else float(our_df["gift_income"].mean())
    our_avg_engagement = our_predicted_engagement if our_predicted_engagement is not None else float(our_df["engagement_rate"].mean())

    comp_avg_peak = float(competitor_df["avg_peak_viewers"].mean())
    comp_avg_income = float(competitor_df["avg_gift_income"].mean())
    comp_avg_engagement = float(competitor_df["avg_engagement_rate"].mean())

    gaps: List[CompetitorGap] = []

    def _gap(metric: str, our: float, comp: float, unit: str = "") -> CompetitorGap:
        gap = our - comp
        pct = gap / max(comp, 1) * 100
        if pct > 20:
            advice = f"{metric}显著领先竞品 {pct:.1f}%，保持优势，可探索差异化变现方式。"
        elif pct > 0:
            advice = f"{metric}略高于竞品 {pct:.1f}%，继续巩固即可。"
        elif pct > -20:
            advice = f"{metric}落后竞品 {abs(pct):.1f}%，需要针对性优化。"
        else:
            advice = f"{metric}显著落后竞品 {abs(pct):.1f}%，建议分析竞品策略后调整运营方向。"
        return CompetitorGap(
            metric=f"{metric}{unit}",
            our_value=round(our, 2),
            competitor_avg=round(comp, 2),
            gap=round(gap, 2),
            pct_gap=round(pct, 1),
            advice=advice,
        )

    gaps.append(_gap("峰值观看人数", our_avg_peak, comp_avg_peak))
    gaps.append(_gap("礼物收入", our_avg_income, comp_avg_income, " ¥"))
    gaps.append(_gap("互动率", our_avg_engagement * 100, comp_avg_engagement * 100, " %"))

    our_category = str(our_df["category"].mode().iloc[0]) if "category" in our_df.columns else ""
    same_cat = competitor_df[competitor_df["category"] == our_category]["competitor_name"].tolist() if our_category else []

    top_competitor = competitor_df.loc[competitor_df["avg_gift_income"].idxmax()]
    top_benchmark = f"{top_competitor['competitor_name']}（{top_competitor['category']}，收入 ¥{top_competitor['avg_gift_income']:,.0f}）"

    total_pct = sum(g.pct_gap for g in gaps) / len(gaps)
    if total_pct > 15:
        summary = "综合表现领先于竞品，建议在保持优势的同时拓展新的增长点。"
    elif total_pct > -15:
        summary = "与竞品水平相当，需要找到差异化突破口。"
    else:
        summary = "综合表现落后于竞品，建议深入研究头部竞品的直播策略与内容形式。"

    return CompetitorReport(
        gaps=gaps,
        same_category_competitors=same_cat,
        top_benchmark=top_benchmark,
        summary=summary,
    )
