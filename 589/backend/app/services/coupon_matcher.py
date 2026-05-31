from typing import List, Dict, Optional
from datetime import date
from sqlalchemy.orm import Session
from ..models.coupon import Coupon
from ..schemas.coupon import CouponMatchRequest


class CouponMatcher:
    def __init__(self, db: Session):
        self.db = db

    def get_active_coupons(self, platform: Optional[str] = None) -> List[Coupon]:
        query = self.db.query(Coupon).filter(
            Coupon.is_active == True,
            Coupon.valid_from <= date.today(),
            Coupon.valid_to >= date.today()
        )
        if platform:
            query = query.filter(Coupon.platform == platform)
        return query.all()

    def match_coupons(self, request: CouponMatchRequest) -> List[Coupon]:
        coupons = self.get_active_coupons(request.platform)
        matched = []

        for coupon in coupons:
            if request.price >= float(coupon.min_amount):
                matched.append(coupon)

        matched.sort(key=lambda c: self._calculate_discount_value(c, request.price), reverse=True)
        return matched

    def _calculate_discount_value(self, coupon: Coupon, price: float) -> float:
        if coupon.discount_type == "percentage":
            discount = price * (float(coupon.discount) / 100)
            if coupon.max_discount:
                discount = min(discount, float(coupon.max_discount))
            return discount
        else:
            return float(coupon.discount)

    def get_best_coupon(self, request: CouponMatchRequest) -> Optional[Dict]:
        matched = self.match_coupons(request)
        if not matched:
            return None

        best = matched[0]
        discount = self._calculate_discount_value(best, request.price)
        final_price = request.price - discount

        return {
            "coupon": best,
            "discount_amount": discount,
            "final_price": final_price,
            "savings_percent": (discount / request.price) * 100 if request.price > 0 else 0
        }

    def get_coupon_summary(self, product_id: str, platform: str, price: float) -> Dict:
        coupons = self.get_active_coupons(platform)
        applicable = [c for c in coupons if price >= float(c.min_amount)]

        if not applicable:
            return {"available": False, "count": 0, "best_discount": 0}

        best = max(applicable, key=lambda c: self._calculate_discount_value(c, price))
        max_discount = self._calculate_discount_value(best, price)

        return {
            "available": True,
            "count": len(applicable),
            "best_discount": max_discount,
            "best_coupon": best,
            "final_price": price - max_discount,
            "savings": (max_discount / price) * 100 if price > 0 else 0
        }

    def get_platform_coupon_stats(self) -> Dict[str, Dict]:
        platforms = ["taobao", "jd", "pdd", "suning", "tmall"]
        stats = {}

        for platform in platforms:
            coupons = self.get_active_coupons(platform)
            stats[platform] = {
                "total_coupons": len(coupons),
                "avg_discount": sum(float(c.discount) for c in coupons) / len(coupons) if coupons else 0,
                "avg_min_amount": sum(float(c.min_amount) for c in coupons) / len(coupons) if coupons else 0
            }

        return stats
