from __future__ import annotations

import numpy as np
import pandas as pd


CN_HOLIDAYS_2026: list[str] = [
    "2026-01-01", "2026-01-02", "2026-01-03",
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-04", "2026-04-05", "2026-04-06",
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
    "2026-06-19", "2026-06-20", "2026-06-21",
    "2026-09-25", "2026-09-26", "2026-09-27",
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07",
]

PLATFORM_EVENTS_2026: dict[str, float] = {
    "2026-01-01": 0.8,
    "2026-02-14": 0.6,
    "2026-03-08": 0.4,
    "2026-05-20": 0.5,
    "2026-06-18": 0.7,
    "2026-08-18": 0.7,
    "2026-11-11": 0.9,
    "2026-12-12": 0.8,
    "2026-12-24": 0.5,
    "2026-12-31": 0.8,
}

AGE_BUCKET_COLUMNS: list[str] = ["age_18_24", "age_25_34", "age_35_44", "age_45_plus"]

GENDER_AGE_COLUMNS: list[str] = ["male_pct"] + AGE_BUCKET_COLUMNS

TARGET_COLUMNS_EXT: list[str] = [
    "peak_viewers", "gift_income", "engagement_rate",
    "male_pct", "age_18_24", "age_25_34", "age_35_44", "age_45_plus",
]


def is_cn_holiday(date_str: str) -> int:
    return int(date_str in CN_HOLIDAYS_2026)


def get_platform_activity(date_str: str) -> float:
    return float(PLATFORM_EVENTS_2026.get(date_str, 0.0))


def _sample_age_distribution(rng: np.random.Generator) -> tuple[float, float, float, float]:
    raw = rng.dirichlet([3.5, 4.0, 2.0, 1.0])
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _sample_male_pct(rng: np.random.Generator, category: str) -> float:
    if category == "游戏":
        base = rng.uniform(0.55, 0.80)
    elif category == "户外":
        base = rng.uniform(0.50, 0.75)
    elif category == "音乐":
        base = rng.uniform(0.30, 0.60)
    elif category == "聊天":
        base = rng.uniform(0.35, 0.65)
    else:
        base = rng.uniform(0.40, 0.65)
    return float(np.clip(base, 0.05, 0.95))


def generate_sample_data(n_days: int = 60, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp("2026-01-01")
    rows = []
    base_viewers = 5000
    base_engagement = 0.05
    for i in range(n_days):
        date = start_date + pd.Timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        hour = int(rng.choice([10, 14, 19, 20, 21, 22, 23], p=[0.05, 0.1, 0.2, 0.25, 0.2, 0.15, 0.05]))
        weekday = date.dayofweek
        duration = float(np.clip(rng.normal(3.5, 0.8), 1.0, 8.0))
        hour_bonus = 1.0 + 0.3 * (hour in (19, 20, 21, 22))
        day_bonus = 1.0 + 0.15 * (weekday >= 5)
        holiday = is_cn_holiday(date_str)
        activity = get_platform_activity(date_str)
        holiday_bonus = 1.0 + 0.4 * holiday
        activity_bonus = 1.0 + 0.5 * activity
        trend = 1.0 + 0.004 * i
        categories = ["游戏", "音乐", "聊天", "户外", "教育"]
        category = str(rng.choice(categories))
        peak_viewers = int(base_viewers * hour_bonus * day_bonus * holiday_bonus * activity_bonus * trend * rng.uniform(0.85, 1.2))
        engagement = float(np.clip(
            base_engagement * hour_bonus * day_bonus * holiday_bonus * rng.uniform(0.8, 1.25),
            0.005, 0.25,
        ))
        income = float(round(peak_viewers * duration * engagement * (1.0 + 0.3 * activity) * rng.uniform(0.8, 1.3), 2))
        male_pct = _sample_male_pct(rng, category)
        a18, a25, a35, a45 = _sample_age_distribution(rng)
        rows.append(
            {
                "date": date_str,
                "start_hour": hour,
                "weekday": int(weekday),
                "is_holiday": holiday,
                "platform_activity": activity,
                "category": category,
                "duration_hours": float(np.round(duration, 2)),
                "peak_viewers": int(peak_viewers),
                "avg_viewers": int(peak_viewers * rng.uniform(0.4, 0.7)),
                "engagement_rate": float(np.round(engagement, 4)),
                "gift_income": float(np.round(income, 2)),
                "male_pct": float(np.round(male_pct, 4)),
                "age_18_24": float(np.round(a18, 4)),
                "age_25_34": float(np.round(a25, 4)),
                "age_35_44": float(np.round(a35, 4)),
                "age_45_plus": float(np.round(a45, 4)),
            }
        )
    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def generate_sample_competitors(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    competitor_names = ["竞技小王", "音乐天后", "聊天达人", "户外探险家", "知识一哥"]
    categories = ["游戏", "音乐", "聊天", "户外", "教育"]
    rows = []
    for name, cat in zip(competitor_names, categories):
        base_p = rng.integers(3000, 12000)
        base_i = rng.uniform(2000, 15000)
        rows.append({
            "competitor_name": name,
            "category": cat,
            "avg_peak_viewers": int(base_p),
            "avg_gift_income": float(np.round(base_i, 2)),
            "avg_engagement_rate": float(np.round(rng.uniform(0.03, 0.12), 4)),
            "avg_duration_hours": float(np.round(rng.uniform(2.5, 4.5), 1)),
            "follower_count": int(rng.integers(50000, 500000)),
        })
    return pd.DataFrame(rows)
