from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta


class User(BaseModel):
    user_id: int
    username: str
    age: Optional[int] = None
    gender: Optional[str] = None
    favorite_genres: Optional[List[str]] = None
    registration_date: datetime = datetime.now()


class Book(BaseModel):
    book_id: int
    title: str
    author: str
    genres: List[str]
    year: Optional[int] = None
    avg_rating: float = 0.0
    total_ratings: int = 0
    total_pages: Optional[int] = None
    series_id: Optional[int] = None
    series_order: Optional[int] = None


class BookSeries(BaseModel):
    series_id: int
    series_name: str
    author: str
    description: Optional[str] = None
    total_books: int = 0


class ReadingProgress(BaseModel):
    user_id: int
    book_id: int
    current_page: int = 0
    total_pages: Optional[int] = None
    start_date: Optional[datetime] = None
    last_read_date: Optional[datetime] = None
    reading_days: List[datetime] = []
    pages_per_day_avg: float = 0.0
    status: str = "reading"


class ReadingPrediction(BaseModel):
    book_id: int
    current_page: int
    total_pages: int
    pages_per_day: float
    estimated_days_left: float
    estimated_finish_date: datetime
    progress_percent: float


class BookReviewSummary(BaseModel):
    book_id: int
    summary: str
    pros: List[str]
    cons: List[str]
    key_themes: List[str]
    target_audience: List[str]
    generated_at: datetime = datetime.now()


class Rating(BaseModel):
    user_id: int
    book_id: int
    rating: float
    timestamp: datetime = datetime.now()


class SocialConnection(BaseModel):
    user_id: int
    friend_id: int
    connection_strength: float = 1.0


class RecommendationRequest(BaseModel):
    user_id: int
    top_n: int = 10
    diversity_weight: float = 0.3
    exploration_rate: float = 0.2


class RecommendationResult(BaseModel):
    book_id: int
    title: str
    score: float
    reason: str
    genres: List[str]


class UserProfile(BaseModel):
    user_id: int
    read_books: List[int]
    ratings: Dict[int, float]
    friends: List[int]
    favorite_genres: List[str]
