from typing import List, Dict, Tuple, Optional
from models.schemas import (
    Dish, DishSubstitute, SubstituteReason,
    CartSubstitutionResponse, Allergen, User
)


class DishSubstituteEngine:
    def __init__(self, dishes: Dict[str, Dish]):
        self.dishes = dishes
        self.dish_categories = self._build_dish_categories()
    
    def _build_dish_categories(self) -> Dict[str, List[str]]:
        categories = {
            "hot_pot": [],
            "fish": [],
            "chicken": [],
            "pork": [],
            "beef": [],
            "seafood": [],
            "vegetarian": [],
            "soup": [],
            "noodle_rice": [],
            "appetizer": [],
            "dessert": []
        }
        
        meat_tags = {
            "fish": ["鱼", "草鱼", "鲈鱼", "黑鱼"],
            "chicken": ["鸡", "土鸡", "三黄鸡", "鸡胸肉"],
            "pork": ["猪", "五花肉", "里脊", "梅花肉"],
            "beef": ["牛", "牛肉"],
            "seafood": ["虾", "海参", "海鲜", "贝类", "蟹"]
        }
        
        for dish_id, dish in self.dishes.items():
            ings = set(dish.ingredients)
            
            if "锅底" in dish.name or "火锅" in dish.name:
                categories["hot_pot"].append(dish_id)
                continue
            
            categorized = False
            for cat, keywords in meat_tags.items():
                has_ingredient = any(k in ing for k in keywords for ing in dish.ingredients)
                has_name = any(k in dish.name for k in keywords)
                if has_ingredient or has_name:
                    categories[cat].append(dish_id)
                    categorized = True
            
            if not categorized:
                is_vegetarian = True
                for cat, keywords in meat_tags.items():
                    if any(k in ing for k in keywords for ing in dish.ingredients):
                        is_vegetarian = False
                        break
                if is_vegetarian:
                    categories["vegetarian"].append(dish_id)
            
            if "汤" in dish.name or "羹" in dish.name:
                categories["soup"].append(dish_id)
            
            if "米线" in dish.name or "面" in dish.name or "饭" in dish.name:
                categories["noodle_rice"].append(dish_id)
        
        return categories
    
    def calculate_dish_similarity(self, dish1: Dish, dish2: Dish) -> float:
        score = 0.0
        
        if dish1.cuisine == dish2.cuisine:
            score += 0.2
        
        common_tastes = set(dish1.taste_tags) & set(dish2.taste_tags)
        score += min(len(common_tastes) * 0.15, 0.45)
        
        common_ingredients = set(dish1.ingredients) & set(dish2.ingredients)
        score += min(len(common_ingredients) * 0.1, 0.2)
        
        price_diff = abs(dish1.price - dish2.price)
        if price_diff <= 10:
            score += 0.15
        elif price_diff <= 30:
            score += 0.1
        
        if dish1.season and dish2.season and dish1.season == dish2.season:
            score += 0.1
        
        return min(score, 1.0)
    
    def find_substitutes(
        self,
        dish_id: str,
        reason: SubstituteReason,
        user: Optional[User] = None,
        exclude_allergens: List[Allergen] = None,
        top_n: int = 3
    ) -> List[DishSubstitute]:
        if dish_id not in self.dishes:
            return []
        
        original_dish = self.dishes[dish_id]
        candidates = []
        
        for other_id, other_dish in self.dishes.items():
            if other_id == dish_id:
                continue
            
            if not other_dish.is_available or other_dish.stock_quantity <= 0:
                continue
            
            if exclude_allergens:
                dish_allergens = set(other_dish.allergens)
                if dish_allergens & set(exclude_allergens):
                    continue
            
            if user:
                user_disliked = set(user.preferences.disliked_ingredients)
                dish_ings = set(other_dish.ingredients)
                if user_disliked & dish_ings:
                    continue
            
            similarity = self.calculate_dish_similarity(original_dish, other_dish)
            
            if similarity >= 0.3:
                candidates.append((other_id, other_dish, similarity))
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        substitutes = []
        for cand_id, cand_dish, similarity in candidates[:top_n]:
            explanation = self._generate_explanation(original_dish, cand_dish, similarity, reason)
            
            substitutes.append(DishSubstitute(
                original_dish_id=dish_id,
                original_dish_name=original_dish.name,
                substitute_dish_id=cand_id,
                substitute_dish_name=cand_dish.name,
                similarity_score=similarity,
                substitute_reason=reason,
                price_difference=cand_dish.price - original_dish.price,
                explanation=explanation
            ))
        
        return substitutes
    
    def _generate_explanation(
        self,
        original: Dish,
        substitute: Dish,
        similarity: float,
        reason: SubstituteReason
    ) -> str:
        parts = []
        
        if reason == SubstituteReason.SOLD_OUT:
            parts.append(f"{original.name}已沽清")
        elif reason == SubstituteReason.ALLERGY_CONFLICT:
            parts.append(f"为您避免过敏源")
        elif reason == SubstituteReason.NUTRITION_BALANCE:
            parts.append("为营养均衡推荐")
        
        if original.cuisine == substitute.cuisine:
            parts.append(f"同属{original.cuisine}")
        
        common_tastes = set(original.taste_tags) & set(substitute.taste_tags)
        if common_tastes:
            parts.append(f"口味相似（{', '.join(common_tastes)}）")
        
        if similarity >= 0.7:
            parts.append("高度相似")
        elif similarity >= 0.5:
            parts.append("较为相似")
        
        return "，".join(parts)
    
    def substitute_sold_out_dishes(
        self,
        cart_dish_ids: List[str],
        user: Optional[User] = None
    ) -> CartSubstitutionResponse:
        substitutions = []
        final_cart = []
        total_price_change = 0.0
        
        for dish_id in cart_dish_ids:
            if dish_id not in self.dishes:
                final_cart.append(dish_id)
                continue
            
            dish = self.dishes[dish_id]
            
            if dish.is_available and dish.stock_quantity > 0:
                final_cart.append(dish_id)
                continue
            
            allergens = list(user.allergens) if user else None
            substitutes = self.find_substitutes(
                dish_id,
                SubstituteReason.SOLD_OUT,
                user=user,
                exclude_allergens=allergens,
                top_n=1
            )
            
            if substitutes:
                sub = substitutes[0]
                substitutions.append(sub)
                final_cart.append(sub.substitute_dish_id)
                total_price_change += sub.price_difference
            else:
                final_cart.append(dish_id)
        
        return CartSubstitutionResponse(
            original_cart=cart_dish_ids,
            substitutions=substitutions,
            final_cart=final_cart,
            total_price_change=total_price_change
        )
    
    def get_category_alternatives(self, category: str, top_n: int = 5) -> List[str]:
        return self.dish_categories.get(category, [])[:top_n]
    
    def mark_as_sold_out(self, dish_id: str) -> bool:
        if dish_id in self.dishes:
            self.dishes[dish_id].is_available = False
            self.dishes[dish_id].stock_quantity = 0
            return True
        return False
    
    def update_stock(self, dish_id: str, quantity: int) -> bool:
        if dish_id in self.dishes:
            self.dishes[dish_id].stock_quantity = quantity
            self.dishes[dish_id].is_available = quantity > 0
            return True
        return False
