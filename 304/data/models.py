from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np


@dataclass
class User:
    user_id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    registration_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'age': self.age,
            'gender': self.gender,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None
        }


@dataclass
class News:
    news_id: int
    title: str
    category: str
    category_id: int
    content: str
    publish_time: datetime
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'news_id': self.news_id,
            'title': self.title,
            'category': self.category,
            'category_id': self.category_id,
            'content': self.content,
            'publish_time': self.publish_time.isoformat(),
            'author': self.author,
            'tags': self.tags
        }


@dataclass
class UserBehavior:
    user_id: int
    news_id: int
    behavior_type: str
    timestamp: datetime
    duration: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'news_id': self.news_id,
            'behavior_type': self.behavior_type,
            'timestamp': self.timestamp.isoformat(),
            'duration': self.duration
        }


@dataclass
class UserProfile:
    user_id: int
    category_preferences: Dict[str, float] = field(default_factory=dict)
    recent_behavior: List[Dict] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'category_preferences': self.category_preferences,
            'recent_behavior': self.recent_behavior,
            'embedding': self.embedding.tolist() if self.embedding is not None else None,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class NewsFeatures:
    news_id: int
    category_id: int
    popularity_score: float = 0.0
    embedding: Optional[np.ndarray] = None
    hot_score: float = 0.0
    click_count: int = 0
    like_count: int = 0
    share_count: int = 0

    def to_dict(self) -> Dict:
        return {
            'news_id': self.news_id,
            'category_id': self.category_id,
            'popularity_score': self.popularity_score,
            'embedding': self.embedding.tolist() if self.embedding is not None else None,
            'hot_score': self.hot_score,
            'click_count': self.click_count,
            'like_count': self.like_count,
            'share_count': self.share_count
        }


@dataclass
class RecommendationResult:
    news_id: int
    score: float
    category: str
    rank: int
    is_hot: bool = False
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            'news_id': self.news_id,
            'score': float(self.score),
            'category': self.category,
            'rank': self.rank,
            'is_hot': self.is_hot,
            'reason': self.reason
        }
