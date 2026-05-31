from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from ..models.price import PlatformPrice
from ..models.product import Product
from ..schemas.price import ComparisonResult, PlatformPrice as PlatformPriceSchema, PriceHistory
from .price_analyzer import PriceAnalyzer


class SmartComparator:
    PLATFORM_WEIGHTS = {
        "taobao": {"trust": 0.9, "shipping": 0.85, "return": 0.9},
        "jd": {"trust": 0.95, "shipping": 0.95, "return": 0.9},
        "pdd": {"trust": 0.75, "shipping": 0.8, "return": 0.7},
        "suning": {"trust": 0.85, "shipping": 0.85, "return": 0.85},
        "tmall": {"trust": 0.92, "shipping": 0.88, "return": 0.88},
    }

    def __init__(self, db: Session, history_db: Session):
        self.db = db
        self.history_db = history_db
        self.analyzer = PriceAnalyzer(db, history_db)

    def compare_prices(self, product: Product, coupons: List = None) -> ComparisonResult:
        prices = self.db.query(PlatformPrice).filter(
            PlatformPrice.product_id == product.id
        ).all()

        if not prices:
            return ComparisonResult(
                product=product,
                prices=[],
                best_deal=None,
                lowest_ever=0,
                price_history=[],
                potential_savings=0
            )

        price_schemas = []
        for p in prices:
            price_schema = PlatformPriceSchema.model_validate(p)
            if coupons:
                matched_coupons = [c for c in coupons if c.platform == p.platform]
                price_schema.coupons = matched_coupons
                price_schema.coupon_price = self._calculate_coupon_price(
                    float(p.price), matched_coupons
                )
            price_schemas.append(price_schema)

        best_deal = self._find_best_deal(price_schemas)
        lowest_ever = self._get_lowest_ever(product.id)
        history = self.analyzer.get_price_history(product.id, days=90)
        potential_savings = self._calculate_potential_savings(price_schemas, lowest_ever)

        return ComparisonResult(
            product=product,
            prices=sorted(price_schemas, key=lambda x: x.coupon_price or x.price),
            best_deal=best_deal,
            lowest_ever=lowest_ever,
            price_history=[
                PriceHistory(date=h.record_date, price=float(h.price), platform=h.platform)
                for h in history
            ],
            potential_savings=potential_savings
        )

    def _find_best_deal(self, prices: List[PlatformPriceSchema]) -> PlatformPriceSchema:
        if not prices:
            return None

        scored_prices = []
        for p in prices:
            if not p.in_stock:
                continue

            final_price = p.coupon_price or p.price
            score = self._calculate_comprehensive_score(p, final_price)
            scored_prices.append((score, p, final_price))

        if not scored_prices:
            return prices[0]

        scored_prices.sort(key=lambda x: x[0], reverse=True)
        return scored_prices[0][1]

    def _calculate_comprehensive_score(self, price: PlatformPriceSchema, final_price: float) -> float:
        base_score = 1000.0

        price_score = 500 * (1 - (final_price / self._get_max_price(price) if final_price > 0 else 0))

        platform_weights = self.PLATFORM_WEIGHTS.get(price.platform, {"trust": 0.8, "shipping": 0.8, "return": 0.8})
        platform_score = 200 * (
            platform_weights["trust"] * 0.4 +
            platform_weights["shipping"] * 0.3 +
            platform_weights["return"] * 0.3
        )

        rating_score = 150 * (price.rating / 5.0 if price.rating else 0.5)

        sales_score = 100 * min(price.sales / 10000, 1.0) if price.sales else 50

        stock_bonus = 50 if price.in_stock else -100

        coupon_bonus = 30 if price.coupon_price and price.coupon_price < price.price else 0

        total_score = price_score + platform_score + rating_score + sales_score + stock_bonus + coupon_bonus

        return total_score

    def _get_max_price(self, current_price: PlatformPriceSchema) -> float:
        return max(float(current_price.price), float(current_price.original_price or current_price.price))

    def _calculate_coupon_price(self, price: float, coupons: List) -> Optional[float]:
        if not coupons:
            return None

        max_discount = 0
        for coupon in coupons:
            if price >= float(coupon.min_amount):
                if coupon.discount_type == "percentage":
                    discount = price * (float(coupon.discount) / 100)
                    if coupon.max_discount:
                        discount = min(discount, float(coupon.max_discount))
                else:
                    discount = float(coupon.discount)
                max_discount = max(max_discount, discount)

        return price - max_discount if max_discount > 0 else None

    def _get_lowest_ever(self, product_id: str) -> float:
        history = self.history_db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id
        ).all()
        if not history:
            return 0
        return min(float(h.price) for h in history)

    def _calculate_potential_savings(self, prices: List[PlatformPriceSchema], lowest_ever: float) -> float:
        if not prices:
            return 0

        highest_price = max(float(p.original_price or p.price) for p in prices)
        current_best = min(float(p.coupon_price or p.price) for p in prices if p.in_stock)

        return max(highest_price - current_best, current_best - lowest_ever if lowest_ever > 0 else 0)

    def get_price_comparison_summary(self, product_id: str) -> Dict:
        prices = self.db.query(PlatformPrice).filter(
            PlatformPrice.product_id == product_id
        ).all()

        if not prices:
            return {}

        in_stock_prices = [float(p.price) for p in prices if p.in_stock]
        all_prices = [float(p.price) for p in prices]

        return {
            "platform_count": len(set(p.platform for p in prices)),
            "in_stock_count": len([p for p in prices if p.in_stock]),
            "current_lowest": min(in_stock_prices) if in_stock_prices else 0,
            "current_highest": max(all_prices) if all_prices else 0,
            "price_range": max(all_prices) - min(all_prices) if all_prices else 0,
            "average_price": sum(all_prices) / len(all_prices) if all_prices else 0,
            "best_platform": self._get_best_platform_name(prices)
        }

    def _get_best_platform_name(self, prices: List[PlatformPrice]) -> str:
        in_stock = [p for p in prices if p.in_stock]
        if not in_stock:
            return prices[0].platform_name if prices else ""
        best = min(in_stock, key=lambda p: float(p.price))
        return best.platform_name
