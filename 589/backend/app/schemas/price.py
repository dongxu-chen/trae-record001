from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from .product import Product
from .coupon import Coupon


class PlatformPriceBase(BaseModel):
    product_id: str
    platform: str = Field(..., max_length=50)
    platform_name: str = Field(..., max_length=50)
    price: float
    original_price: Optional[float] = None
    product_url: str = Field(..., max_length=1000)
    in_stock: bool = True
    rating: Optional[float] = None
    sales: int = 0


class PlatformPriceCreate(PlatformPriceBase):
    pass


class PlatformPrice(PlatformPriceBase):
    id: str
    last_updated: datetime
    coupons: List[Coupon] = []
    coupon_price: Optional[float] = None

    class Config:
        from_attributes = True


class PriceHistory(BaseModel):
    date: date
    price: float
    platform: str

    class Config:
        from_attributes = True


class ComparisonResult(BaseModel):
    product: Product
    prices: List[PlatformPrice]
    best_deal: PlatformPrice
    lowest_ever: float
    price_history: List[PriceHistory]
    potential_savings: float
