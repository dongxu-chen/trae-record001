from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.coupon import Coupon
from ..schemas.coupon import CouponCreate, Coupon as CouponSchema, CouponMatchRequest
from ..services import CouponMatcher

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("/", response_model=List[CouponSchema])
def get_coupons(
    platform: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    matcher = CouponMatcher(db)
    coupons = matcher.get_active_coupons(platform)
    return [CouponSchema.model_validate(c) for c in coupons]


@router.post("/match")
def match_coupons(request: CouponMatchRequest, db: Session = Depends(get_db)):
    matcher = CouponMatcher(db)
    matched = matcher.match_coupons(request)
    return {
        "matched": [CouponSchema.model_validate(c) for c in matched],
        "count": len(matched),
        "best_deal": matcher.get_best_coupon(request)
    }


@router.get("/summary")
def get_coupon_summary(
    product_id: str,
    platform: str,
    price: float,
    db: Session = Depends(get_db)
):
    matcher = CouponMatcher(db)
    request = CouponMatchRequest(product_id=product_id, platform=platform, price=price)
    return matcher.get_coupon_summary(product_id, platform, price)


@router.get("/stats")
def get_platform_stats(db: Session = Depends(get_db)):
    matcher = CouponMatcher(db)
    return matcher.get_platform_coupon_stats()


@router.post("/", response_model=CouponSchema)
def create_coupon(coupon_data: CouponCreate, db: Session = Depends(get_db)):
    coupon = Coupon(**coupon_data.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return CouponSchema.model_validate(coupon)


@router.get("/{coupon_id}", response_model=CouponSchema)
def get_coupon(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return CouponSchema.model_validate(coupon)


@router.put("/{coupon_id}/deactivate")
def deactivate_coupon(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    coupon.is_active = False
    db.commit()
    return {"success": True}
