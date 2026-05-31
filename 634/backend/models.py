from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class TopicLifeCycle(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    BURSTING = "bursting"
    DECLINING = "declining"
    STABLE = "stable"

class NewsArticle(BaseModel):
    id: str
    title: str
    content: str
    source: str
    publish_time: datetime
    url: Optional[str] = None
    author: Optional[str] = None
    share_count: int = 0
    like_count: int = 0
    comment_count: int = 0

class ClusterTopic(BaseModel):
    topic_id: str
    name: str
    keywords: List[str]
    articles: List[str]
    centroid: List[float]
    size: int
    created_at: datetime
    updated_at: datetime
    lifecycle: TopicLifeCycle
    influence_score: float
    trend_score: float
    burst_count: int
    total_shares: int = 0
    total_likes: int = 0
    total_comments: int = 0

class TopicEvolution(BaseModel):
    from_topic: str
    to_topic: str
    evolution_type: str
    similarity: float
    timestamp: datetime
    common_keywords: List[str]

class InfluenceMetrics(BaseModel):
    topic_id: str
    reach: int
    engagement: float
    velocity: float
    momentum: float
    share_score: float
    overall_score: float

class TopicSnapshot(BaseModel):
    topic_id: str
    name: str
    keywords: List[str]
    size: int
    lifecycle: TopicLifeCycle
    influence: InfluenceMetrics
    timestamp: datetime

class TopicWarning(BaseModel):
    warning_id: str
    topic_id: str
    topic_name: str
    warning_level: str
    warning_type: str
    confidence: float
    predicted_burst_time: Optional[datetime] = None
    current_metrics: Dict
    historical_trend: List[Dict]
    created_at: datetime
    message: str

class PropagationNode(BaseModel):
    article_id: str
    title: str
    source: str
    publish_time: datetime
    share_count: int
    like_count: int
    comment_count: int
    influence_score: float
    is_ignition_point: bool = False
    propagation_level: int = 0

class PropagationPath(BaseModel):
    topic_id: str
    topic_name: str
    ignition_points: List[PropagationNode]
    propagation_tree: List[Dict]
    total_propagation_depth: int
    key_influencers: List[Dict]
    analyzed_at: datetime

class TopicComparisonItem(BaseModel):
    topic_id: str
    topic_name: str
    lifecycle_timeline: List[Dict]
    size_history: List[Dict]
    influence_history: List[Dict]
    social_history: List[Dict]
    peak_time: Optional[datetime] = None
    peak_size: int
    total_duration_hours: float

class TopicComparisonResult(BaseModel):
    comparison_id: str
    topics: List[TopicComparisonItem]
    time_range_start: datetime
    time_range_end: datetime
    metrics: Dict
    created_at: datetime

class WebSocketMessage(BaseModel):
    type: str
    data: Dict
    timestamp: datetime
