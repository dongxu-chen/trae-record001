import json
import os
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "analysis_history.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def to_utc_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_utc_datetime(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip().rstrip('Z')
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    return None
    return to_utc_datetime(dt)


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    dt_utc = to_utc_datetime(dt)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def save_analysis_history(username: str, summary: dict, results: List[dict]):
    ensure_data_dir()
    history = load_history()
    entry = {
        "timestamp": format_utc_iso(get_utc_now()),
        "username": username,
        "summary": summary,
        "results_count": len(results),
        "fake_ratio": summary.get("fake_ratio", 0),
        "genuine_count": summary.get("genuine_count", 0),
        "suspicious_count": summary.get("suspicious_count", 0),
        "fake_count": summary.get("fake_count", 0),
        "likely_fake_count": summary.get("likely_fake_count", 0),
    }
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_history() -> List[dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_trend_data() -> pd.DataFrame:
    history = load_history()
    if not history:
        return pd.DataFrame(columns=["timestamp", "username", "fake_ratio", "genuine_count", "suspicious_count", "fake_count", "likely_fake_count"])
    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")
    return df


def generate_mock_followers(count: int = 100, fake_ratio: float = 0.3, seed: Optional[int] = None) -> List[dict]:
    if seed is not None:
        np.random.seed(seed)

    now = get_utc_now()
    followers = []
    fake_count = int(count * fake_ratio)
    genuine_count = count - fake_count

    for i in range(genuine_count):
        age_days = np.random.randint(180, 3000)
        reg_date = now - timedelta(days=age_days)
        followers_count = int(np.random.lognormal(5, 2))
        following_count = int(np.random.lognormal(4, 1.5))
        posts_count = int(np.random.lognormal(5, 1.5))
        likes_count = int(np.random.lognormal(6, 2))
        engagement_rate = np.random.beta(2, 5)
        bio_length = int(np.random.exponential(50))
        repost_ratio = np.random.beta(2, 8)
        mention_ratio = np.random.beta(3, 7)
        hashtag_ratio = np.random.beta(2, 6)
        content_diversity = np.random.beta(5, 2)
        activity_regularity = np.random.beta(5, 2)
        duplicate_content_ratio = np.random.beta(1, 10)

        followers.append({
            "user_id": f"genuine_{i:04d}",
            "username": f"user_genuine_{i:04d}",
            "display_name": f"Genuine User {i}",
            "bio": "A" * bio_length,
            "avatar_url": "",
            "registration_date": format_utc_iso(reg_date),
            "followers_count": followers_count,
            "following_count": following_count,
            "posts_count": posts_count,
            "likes_count": likes_count,
            "is_verified": np.random.random() < 0.05,
            "is_protected": np.random.random() < 0.1,
            "status": "active",
            "last_activity": format_utc_iso(now - timedelta(days=np.random.randint(0, 30))),
            "avg_daily_posts": np.random.exponential(2),
            "engagement_rate": engagement_rate,
            "content_diversity": content_diversity,
            "has_profile_image": np.random.random() < 0.95,
            "bio_length": bio_length,
            "repost_ratio": repost_ratio,
            "mention_ratio": mention_ratio,
            "hashtag_ratio": hashtag_ratio,
            "activity_regularity": activity_regularity,
            "duplicate_content_ratio": duplicate_content_ratio,
        })

    for i in range(fake_count):
        age_days = np.random.randint(1, 180)
        reg_date = now - timedelta(days=age_days)
        followers_count = int(np.random.lognormal(1, 1))
        following_count = int(np.random.lognormal(6, 1.5))
        posts_count = int(np.random.lognormal(1, 1))
        likes_count = int(np.random.lognormal(1, 1))
        engagement_rate = np.random.beta(1, 20)
        bio_length = int(np.random.exponential(5))
        repost_ratio = np.random.beta(8, 2)
        mention_ratio = np.random.beta(1, 10)
        hashtag_ratio = np.random.beta(8, 2)
        content_diversity = np.random.beta(1, 8)
        activity_regularity = np.random.beta(1, 8)
        duplicate_content_ratio = np.random.beta(8, 2)

        followers.append({
            "user_id": f"fake_{i:04d}",
            "username": f"user_fake_{i:04d}",
            "display_name": f"User{np.random.randint(100000, 999999)}",
            "bio": "A" * bio_length,
            "avatar_url": "",
            "registration_date": format_utc_iso(reg_date),
            "followers_count": followers_count,
            "following_count": following_count,
            "posts_count": posts_count,
            "likes_count": likes_count,
            "is_verified": False,
            "is_protected": np.random.random() < 0.05,
            "status": np.random.choice(["active", "inactive", "dormant"], p=[0.3, 0.3, 0.4]),
            "last_activity": format_utc_iso(now - timedelta(days=np.random.randint(30, 365))),
            "avg_daily_posts": np.random.exponential(0.1),
            "engagement_rate": engagement_rate,
            "content_diversity": content_diversity,
            "has_profile_image": np.random.random() < 0.3,
            "bio_length": bio_length,
            "repost_ratio": repost_ratio,
            "mention_ratio": mention_ratio,
            "hashtag_ratio": hashtag_ratio,
            "activity_regularity": activity_regularity,
            "duplicate_content_ratio": duplicate_content_ratio,
        })

    np.random.shuffle(followers)
    return followers


def get_cleaning_recommendations(fake_ratio: float, risk_factors: Dict[str, int]) -> List[str]:
    recommendations = []

    if fake_ratio > 0.5:
        recommendations.append("严重警告：超过50%的粉丝被标注为高风险，建议立即启动人工审核流程。")
        recommendations.append("建议按虚假概率降序排序，优先审核风险最高的账号。")
    elif fake_ratio > 0.3:
        recommendations.append("警告：约30%-50%的粉丝被标注为可疑，建议分批进行人工审核。")
    elif fake_ratio > 0.15:
        recommendations.append("注意：约15%-30%的粉丝存在可疑特征，建议定期标注和人工复核。")
    else:
        recommendations.append("您的粉丝质量较好，风险账号比例较低。建议保持定期监控。")

    recommendations.append("所有可疑账号已自动标注，建议人工逐个审核后再决定是否移除，以避免误删真实用户。")

    sorted_factors = sorted(risk_factors.items(), key=lambda x: x[1], reverse=True)
    for factor, count in sorted_factors[:3]:
        if factor == "low_engagement":
            recommendations.append(f"有 {count} 个账号互动率极低，已自动标注为「低互动」，建议人工核实是否为僵尸粉。")
        elif factor == "high_following_ratio":
            recommendations.append(f"有 {count} 个账号关注/粉丝比例异常偏高（典型刷粉特征），已标注为「高关注比」，建议人工审核后处理。")
        elif factor == "new_account":
            recommendations.append(f"有 {count} 个新注册账号（<30天）表现出可疑行为，已标注为「新号可疑」，建议观察7-14天后再决定。")
        elif factor == "no_profile_image":
            recommendations.append(f"有 {count} 个账号无头像，已标注为「无头像」，建议人工确认是否为真实用户。")
        elif factor == "high_repost_ratio":
            recommendations.append(f"有 {count} 个账号几乎只转发无原创内容，已标注为「高转发比」，建议人工检查是否为机器账号。")
        elif factor == "duplicate_content":
            recommendations.append(f"有 {count} 个账号存在重复内容，已标注为「内容重复」，建议人工核实是否为自动发布脚本。")
        elif factor == "classic_bot_pattern":
            recommendations.append(f"有 {count} 个账号符合典型机器人模式，已标注为「疑似机器人」，建议优先人工审核。")

    recommendations.append("建议每30天进行一次粉丝质量审计，持续监控风险账号比例变化。")
    recommendations.append("避免购买粉丝服务，这类服务提供的粉丝几乎都是虚假账号，会被自动标注为高风险。")
    recommendations.append("审核建议：对于「可疑」和「疑似虚假」级别的账号，优先人工核实其内容、互动历史和关注模式。")
    recommendations.append("可导出标注后的粉丝列表，在社交媒体平台内使用批量管理工具进行人工复核。")

    return recommendations