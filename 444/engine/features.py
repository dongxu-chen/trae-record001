from datetime import datetime
from typing import Dict, Optional
import numpy as np
from models.data_models import FeatureVector
from utils.helpers import parse_utc_datetime, get_utc_now


FEATURE_NAMES = [
    "account_age_days",
    "followers_following_ratio",
    "posting_frequency",
    "engagement_rate",
    "content_diversity",
    "has_profile_image",
    "bio_length",
    "repost_ratio",
    "mention_ratio",
    "hashtag_ratio",
    "followers_count",
    "following_count",
    "posts_count",
    "is_verified",
    "activity_regularity",
    "duplicate_content_ratio",
]


def extract_features(follower: dict) -> FeatureVector:
    now = get_utc_now()

    reg_date_str = follower.get("registration_date")
    reg_date = parse_utc_datetime(reg_date_str)
    if reg_date:
        account_age_days = max((now - reg_date).days, 1)
    else:
        account_age_days = 1

    followers_count = follower.get("followers_count", 0)
    following_count = follower.get("following_count", 0)
    followers_following_ratio = followers_count / max(following_count, 1)

    posts_count = follower.get("posts_count", 0)
    posting_frequency = posts_count / max(account_age_days, 1)

    engagement_rate = follower.get("engagement_rate", 0.0)
    content_diversity = follower.get("content_diversity", 0.0)
    has_profile_image = 1.0 if follower.get("has_profile_image", True) else 0.0
    bio_length = float(follower.get("bio_length", len(follower.get("bio", ""))))
    repost_ratio = follower.get("repost_ratio", 0.0)
    mention_ratio = follower.get("mention_ratio", 0.0)
    hashtag_ratio = follower.get("hashtag_ratio", 0.0)
    is_verified = 1.0 if follower.get("is_verified", False) else 0.0
    activity_regularity = follower.get("activity_regularity", 0.0)
    duplicate_content_ratio = follower.get("duplicate_content_ratio", 0.0)

    return FeatureVector(
        user_id=follower.get("user_id", ""),
        account_age_days=account_age_days,
        followers_following_ratio=followers_following_ratio,
        posting_frequency=posting_frequency,
        engagement_rate=engagement_rate,
        content_diversity=content_diversity,
        has_profile_image=has_profile_image,
        bio_length=bio_length,
        repost_ratio=repost_ratio,
        mention_ratio=mention_ratio,
        hashtag_ratio=hashtag_ratio,
        followers_count=np.log1p(followers_count),
        following_count=np.log1p(following_count),
        posts_count=np.log1p(posts_count),
        is_verified=is_verified,
        activity_regularity=activity_regularity,
        duplicate_content_ratio=duplicate_content_ratio,
    )


def feature_vector_to_array(fv: FeatureVector) -> np.ndarray:
    return np.array([
        fv.account_age_days,
        fv.followers_following_ratio,
        fv.posting_frequency,
        fv.engagement_rate,
        fv.content_diversity,
        fv.has_profile_image,
        fv.bio_length,
        fv.repost_ratio,
        fv.mention_ratio,
        fv.hashtag_ratio,
        fv.followers_count,
        fv.following_count,
        fv.posts_count,
        fv.is_verified,
        fv.activity_regularity,
        fv.duplicate_content_ratio,
    ])


def identify_risk_factors(follower: dict) -> list:
    risks = []
    now = get_utc_now()

    reg_date_str = follower.get("registration_date")
    reg_date = parse_utc_datetime(reg_date_str)
    if reg_date:
        age_days = (now - reg_date).days
        if age_days < 30:
            risks.append("new_account")

    followers_count = follower.get("followers_count", 0)
    following_count = follower.get("following_count", 0)
    if following_count > 0 and followers_count / following_count < 0.1:
        risks.append("high_following_ratio")

    engagement_rate = follower.get("engagement_rate", 0.0)
    if engagement_rate < 0.01:
        risks.append("low_engagement")

    if not follower.get("has_profile_image", True):
        risks.append("no_profile_image")

    repost_ratio = follower.get("repost_ratio", 0.0)
    if repost_ratio > 0.8:
        risks.append("high_repost_ratio")

    duplicate_content_ratio = follower.get("duplicate_content_ratio", 0.0)
    if duplicate_content_ratio > 0.5:
        risks.append("duplicate_content")

    if follower.get("posts_count", 0) < 5 and followers_count < 10 and following_count > 100:
        risks.append("classic_bot_pattern")

    content_diversity = follower.get("content_diversity", 0.0)
    if content_diversity < 0.2:
        risks.append("low_content_diversity")

    bio_length = follower.get("bio_length", len(follower.get("bio", "")))
    if bio_length < 5 and not follower.get("is_verified", False):
        risks.append("empty_bio")

    return risks