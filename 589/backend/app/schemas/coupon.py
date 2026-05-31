from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class CouponBase(BaseModel):
    platform: str = Field(..., max_length=50)
    code: Optional[str] = Field(None, max_length=100)
    discount: float
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    min_amount: float = 0
    max_discount: Optional[float] = None
    valid_from: date
    valid_to: date
    is_active: bool = True


class CouponCreate(CouponBase):
    pass


class Coupon(CouponBase):
    id: str

    class Config:
        from_attributes = True


class CouponMatchRequest(BaseModel):
    product_id: str
    platform: str
    price: float
