from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PriceAlertBase(BaseModel):
    product_id: str
    platform: str = Field(..., max_length=50)
    target_price: float
    notify_type: str = Field("email", pattern="^(email|push|sms)$")
    is_active: bool = True


class PriceAlertCreate(PriceAlertBase):
    pass


class PriceAlertResponse(PriceAlertBase):
    id: str
    current_price: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PriceAlert(PriceAlertBase):
    id: str
    current_price: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteBase(BaseModel):
    product_id: str


class FavoriteCreate(FavoriteBase):
    pass


class Favorite(FavoriteBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
