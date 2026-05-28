from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class FollowerRiskLevel(Enum):
    GENUINE = "genuine"
    SUSPICIOUS = "suspicious"
    LIKELY_FAKE = "likely_fake"
    FAKE = "fake"


class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DORMANT = "dormant"
    SUSPENDED = "suspended"


@dataclass
class FollowerProfile:
    user_id: str
    username: str
    display_name: str
    bio: str
    avatar_url: str
    registration_date: Optional[datetime]
    followers_count: int
    following_count: int
    posts_count: int
    likes_count: int
    is_verified: bool
    is_protected: bool
    status: AccountStatus = AccountStatus.ACTIVE
    last_activity: Optional[datetime] = None
    avg_daily_posts: float = 0.0
    engagement_rate: float = 0.0
    content_diversity: float = 0.0
    has_profile_image: bool = True
    bio_length: int = 0
    repost_ratio: float = 0.0
    mention_ratio: float = 0.0
    hashtag_ratio: float = 0.0


@dataclass
class FeatureVector:
    user_id: str
    account_age_days: float
    followers_following_ratio: float
    posting_frequency: float
    engagement_rate: float
    content_diversity: float
    has_profile_image: float
    bio_length: float
    repost_ratio: float
    mention_ratio: float
    hashtag_ratio: float
    followers_count: float
    following_count: float
    posts_count: float
    is_verified: float
    activity_regularity: float
    duplicate_content_ratio: float


@dataclass
class DetectionResult:
    user_id: str
    username: str
    risk_level: FollowerRiskLevel
    fake_probability: float
    feature_vector: Optional[FeatureVector] = None
    risk_factors: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class AnalysisSummary:
    total_followers: int
    genuine_count: int
    suspicious_count: int
    likely_fake_count: int
    fake_count: int
    fake_ratio: float
    avg_fake_probability: float
    risk_distribution: dict
    top_risk_factors