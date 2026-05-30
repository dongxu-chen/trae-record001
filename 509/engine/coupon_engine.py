from typing import List, Dict, Optional
from datetime import datetime
from models.schemas import (
    Coupon, CouponType, Dish, DishRecommendation,
    CouponRecommendation, AddOnRecommendation, User
)


class CouponEngine:
    def __init__(self, coupons: List[Coupon], dishes: Dict[str, Dish]):
        self.coupons = coupons
        self.dishes = dishes
    
    def get_active_coupons(self) -> List[Coupon]:
        now = datetime.now()
        return [
            c for c in self.coupons
            if c.is_active and c.valid_from <= now <= c.valid_until
        ]
    
    def calculate_cart_total(self, dish_ids: List[str]) -> float:
        total = 0.0
        for dish_id in dish_ids:
            if dish_id in self.dishes:
                total += self.dishes[dish_id].price
        return round(total, 2)
    
    def calculate_savings(self, coupon: Coupon, cart_total: float) -> float:
        if cart_total < coupon.min_order_amount:
            return 0.0
        
        if coupon.coupon_type == CouponType.PERCENTAGE:
            savings = cart_total * (coupon.discount_value / 100)
            if coupon.max_discount:
                savings = min(savings, coupon.max_discount)
            return round(savings, 2)
        
        elif coupon.coupon_type == CouponType.FIXED_AMOUNT:
            return min(coupon.discount_value, cart_total)
        
        elif coupon.coupon_type == CouponType.BUY_N_GET_ONE:
            return 0.0
        
        elif coupon.coupon_type == CouponType.FREE_DELIVERY:
            return coupon.discount_value
        
        return 0.0
    
    def find_applicable_coupons(self, cart_total: float) -> List[Coupon]:
        active_coupons = self.get_active_coupons()
        applicable = []
        
        for coupon in active_coupons:
            if cart_total >= coupon.min_order_amount:
                applicable.append(coupon)
        
        applicable.sort(key=lambda c: self.calculate_savings(c, cart_total), reverse=True)
        return applicable
    
    def get_coupon_recommendations(
        self,
        cart_dish_ids: List[str],
        user: Optional[User] = None,
        top_n: int = 3
    ) -> List[CouponRecommendation]:
        cart_total = self.calculate_cart_total(cart_dish_ids)
        active_coupons = self.get_active_coupons()
        
        recommendations = []
        
        for coupon in active_coupons:
            if cart_total >= coupon.min_order_amount:
                savings = self.calculate_savings(coupon, cart_total)
                if savings > 0:
                    suggestions = self._get_add_on_suggestions(
                        cart_dish_ids, coupon, 0, user
                    )
                    recommendations.append(CouponRecommendation(
                        coupon=coupon,
                        current_total=cart_total,
                        required_amount=coupon.min_order_amount,
                        amount_to_add=0,
                        suggestion_dishes=suggestions,
                        savings_amount=savings
                    ))
            else:
                amount_to_add = coupon.min_order_amount - cart_total
                if amount_to_add <= 100:
                    savings = self.calculate_savings(coupon, coupon.min_order_amount)
                    if savings > amount_to_add * 0.3:
                        suggestions = self._get_add_on_suggestions(
                            cart_dish_ids, coupon, amount_to_add, user
                        )
                        recommendations.append(CouponRecommendation(
                            coupon=coupon,
                            current_total=cart_total,
                            required_amount=coupon.min_order_amount,
                            amount_to_add=round(amount_to_add, 2),
                            suggestion_dishes=suggestions,
                            savings_amount=savings
                        ))
        
        recommendations.sort(key=lambda r: r.savings_amount - r.amount_to_add, reverse=True)
        return recommendations[:top_n]
    
    def _get_add_on_suggestions(
        self,
        cart_dish_ids: List[str],
        coupon: Coupon,
        target_amount: float,
        user: Optional[User] = None,
        top_n: int = 3
    ) -> List[DishRecommendation]:
        cart_set = set(cart_dish_ids)
        candidates = []
        
        for dish_id, dish in self.dishes.items():
            if dish_id in cart_set:
                continue
            
            if not dish.is_available or dish.stock_quantity <= 0:
                continue
            
            if coupon.applicable_cuisines and dish.cuisine not in coupon.applicable_cuisines:
                continue
            
            if coupon.applicable_dish_ids and dish_id not in coupon.applicable_dish_ids:
                continue
            
            if user:
                if set(dish.allergens) & set(user.allergens):
                    continue
                if set(dish.ingredients) & set(user.preferences.disliked_ingredients):
                    continue
            
            price_score = 1.0 - abs(dish.price - target_amount) / max(target_amount, 1.0)
            popularity_score = dish.popularity_score / 10.0
            total_score = price_score * 0.6 + popularity_score * 0.4
            
            candidates.append((dish_id, dish, total_score))
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        suggestions = []
        for dish_id, dish, score in candidates[:top_n]:
            suggestions.append(DishRecommendation(
                dish_id=dish_id,
                dish_name=dish.name,
                score=score,
                reason=f"再加{dish.price:.0f}元即可使用优惠券",
                matched_features=["凑单推荐", "优惠券"]
            ))
        
        return suggestions
    
    def get_add_on_recommendations(
        self,
        cart_dish_ids: List[str],
        user: Optional[User] = None,
        top_n: int = 5
    ) -> List[AddOnRecommendation]:
        cart_total = self.calculate_cart_total(cart_dish_ids)
        active_coupons = self.get_active_coupons()
        
        add_ons = []
        coupon_recommendations = self.get_coupon_recommendations(cart_dish_ids, user, top_n=2)
        
        for rec in coupon_recommendations:
            if rec.amount_to_add > 0:
                for dish_rec in rec.suggestion_dishes[:2]:
                    dish = self.dishes[dish_rec.dish_id]
                    add_ons.append(AddOnRecommendation(
                        add_on_dish=dish_rec,
                        price=dish.price,
                        reason=f"加{dish.price:.0f}元省{rec.savings_amount:.0f}元",
                        contributes_to_coupon=True,
                        coupon_id=rec.coupon.coupon_id
                    ))
        
        cart_set = set(cart_dish_ids)
        popular_candidates = []
        for dish_id, dish in self.dishes.items():
            if dish_id in cart_set:
                continue
            if not dish.is_available:
                continue
            if user:
                if set(dish.allergens) & set(user.allergens):
                    continue
                if set(dish.ingredients) & set(user.preferences.disliked_ingredients):
                    continue
            
            popular_candidates.append((dish_id, dish, dish.popularity_score))
        
        popular_candidates.sort(key=lambda x: x[2], reverse=True)
        
        for dish_id, dish, _ in popular_candidates[:top_n]:
            if len(add_ons) >= top_n:
                break
            if not any(a.add_on_dish.dish_id == dish_id for a in add_ons):
                add_ons.append(AddOnRecommendation(
                    add_on_dish=DishRecommendation(
                        dish_id=dish_id,
                        dish_name=dish.name,
                        score=dish.popularity_score / 10.0,
                        reason="人气推荐，搭配不错",
                        matched_features=["人气加购"]
                    ),
                    price=dish.price,
                    reason="人气加购推荐",
                    contributes_to_coupon=False
                ))
        
        return add_ons[:top_n]
    
    def get_best_coupon(self, cart_total: float) -> Optional[Coupon]:
        applicable = self.find_applicable_coupons(cart_total)
        return applicable[0] if applicable else None
    
    def apply_coupon(self, coupon_id: str, cart_total: float) -> Dict:
        coupon = next((c for c in self.coupons if c.coupon_id == coupon_id), None)
        if not coupon:
            return {"success": False, "message": "优惠券不存在"}
        
        now = datetime.now()
        if not coupon.is_active or not (coupon.valid_from <= now <= coupon.valid_until):
            return {"success": False, "message": "优惠券已过期或未激活"}
        
        if cart_total < coupon.min_order_amount:
            return {
                "success": False,
                "message": f"未达到最低消费{coupon.min_order_amount}元",
                "amount_needed": coupon.min_order_amount - cart_total
            }
        
        savings = self.calculate_savings(coupon, cart_total)
        
        return {
            "success": True,
            "coupon": coupon,
            "original_total": cart_total,
            "savings": savings,
            "final_total": round(cart_total - savings, 2)
        }
