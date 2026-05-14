from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    title: str
    content: str


class PostCreate(PostBase):
    tags: List[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class PostResponse(PostBase):
    id: int
    tags: List[str] = Field(default_factory=list)
    view_count: int = 0
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    author: UserResponse

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    view_count: int = 0
    author_id: int
    author_name: str
    created_at: datetime
    score: Optional[float] = None

    class Config:
        from_attributes = True


class TagCloudItem(BaseModel):
    tag: str
    count: int
    weight: float
    font_size: int


class HotPostResponse(PostResponse):
    total_views: int = 0


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str
