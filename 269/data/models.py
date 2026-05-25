from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Genre(str, Enum):
    POP = "pop"
    ROCK = "rock"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    HIPHOP = "hiphop"
    ELECTRONIC = "electronic"
    COUNTRY = "country"
    RNB = "rnb"


class Song(BaseModel):
    song_id: str
    title: str
    artist: str
    genre: Genre
    year: int
    popularity: float = Field(ge=0, le=1)


class User(BaseModel):
    user_id: str
    name: str
    favorite_genres: List[Genre] = []


class ActionType(str, Enum):
    PLAY = "play"
    SKIP = "skip"
    LIKE = "like"


class UserBehavior(BaseModel):
    user_id: str
    song_id: str
    action: ActionType
    timestamp: datetime
    play_duration: Optional[float] = None


class RecommendationItem(BaseModel):
    song_id: str
    title: str
    artist: str
    genre: Genre
    year: int
    score: float
    reason: str
    source: str


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendationItem]
    timestamp: datetime
