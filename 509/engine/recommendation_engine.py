from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from models.schemas import (
    User, Dish, Order, Season, Allergen,
    DishRecommendation, NutritionAdvice,
    TasteConflict, ActivityLevel
)
from algorithms import CollaborativeFiltering, AssociationRuleMiner, DishKnowledgeGraph
from .taste_conflict_detector import TasteConflictDetector
from .nutrition_calculator import PersonalizedNutritionCalculator


class RecommendationEngine:
    def __init__(self, users: Dict[str, User], dishes: Dict[str, Dish], orders: List[Order]):
        self.users = users
        self.dishes = dishes
        self.orders = orders
        
        self.cf = CollaborativeFiltering(users, dishes, orders)
        self.ar = AssociationRuleMiner(orders, min_support=0.08, min_confidence=0.4)
        self.kg = DishKnowledgeGraph(dishes)
        self.conflict_detector = TasteConflictDetector()
        self.nutrition_calculator = PersonalizedNutritionCalculator()
        
        self.ar.apriori()
        self.ar.generate_rules()
        
        self.dish_taste_map = {d_id: dish.taste_tags for d_id, dish in dishes.items()}
    
    def get_personalized_recommendations(
        self,
        user_id: str,
        current_season: Season,
        exclude_dish_ids: List[str] = None,
        top_n: int = 10,
        budget: Optional[float] = None
    ) -> Tuple[List[DishRecommendation], List[Allergen], List[str]]:
        if exclude_dish_ids is None:
            exclude_dish_ids = []
        
        user = self.users.get(user_id)
        if not user:
            return [], [], []
        
        exclude_dish_ids = list(set(exclude_dish_ids + user.order_history[-3:]))
        
        allergen_free_dishes = self.kg.get_allergen_free_dishes(user.allergens)
        safe_dishes = self.kg.get_dishes_without_ingredients(user.preferences.disliked_ingredients)
        valid_dishes = allergen_free_dishes & safe_dishes
        
        final_exclude = exclude_dish_ids + [d for d in self.dishes if d not in valid_dishes]
        
        scores = defaultdict(float)
        reasons = defaultdict(list)
        matched_features = defaultdict(set)
        
        cf_recs = dict(self.cf.get_combined_recommendations(user_id, n=len(self.dishes), exclude_dishes=final_exclude))
        for dish_id, score in cf_recs.items():
            normalized_score = min(score / 5.0, 1.0) * 0.35
            scores[dish_id] += normalized_score
            reasons[dish_id].append("基于您的点餐历史")
            matched_features[dish_id].add("历史偏好")
        
        pref_recs = dict(self.kg.recommend_based_on_preferences(
            tastes=user.preferences.taste_preferences,
            cuisines=user.preferences.cuisine_preferences,
            allergens=user.allergens,
            top_n=len(self.dishes)
        ))
        for dish_id, score in pref_recs.items():
            if dish_id not in final_exclude:
                scores[dish_id] += score * 0.25
                reasons[dish_id].append("符合您的口味偏好")
                matched_features[dish_id].add("口味匹配")
        
        seasonal_dishes = self.kg.get_seasonal_dishes(current_season)
        for dish_id in seasonal_dishes:
            if dish_id not in final_exclude:
                scores[dish_id] += 0.15
                reasons[dish_id].append(f"{self._season_text(current_season)}时令推荐")
                matched_features[dish_id].add("时令菜品")
        
        for dish_id, dish in self.dishes.items():
            if dish_id not in final_exclude:
                popularity_score = dish.popularity_score / 10.0 * 0.1
                scores[dish_id] += popularity_score
                if popularity_score > 0.05:
                    matched_features[dish_id].add("人气菜品")
                
                if self.nutrition_calculator.has_nutritional_value(dish):
                    scores[dish_id] += 0.05
                    matched_features[dish_id].add("营养丰富")
        
        if budget:
            for dish_id in list(scores.keys()):
                if self.dishes[dish_id].price > budget:
                    del scores[dish_id]
        
        sorted_dishes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for dish_id, score in sorted_dishes[:top_n]:
            dish = self.dishes[dish_id]
            reason = " + ".join(reasons[dish_id]) if reasons[dish_id] else "综合推荐"
            recommendations.append(DishRecommendation(
                dish_id=dish_id,
                dish_name=dish.name,
                score=min(score, 1.0),
                reason=reason,
                matched_features=list(matched_features[dish_id])
            ))
        
        seasonal_recommendations = [
            self.dishes[d].name for d in seasonal_dishes 
            if d in valid_dishes and d not in exclude_dish_ids
        ][:5]
        
        return recommendations, list(user.allergens), seasonal_recommendations
    
    def get_group_recommendations(
        self,
        user_ids: List[str],
        current_season: Season,
        exclude_dish_ids: List[str] = None,
        dishes_per_person: float = 1.5,
        balance_types: List[str] = None,
        budget: Optional[float] = None
    ) -> Tuple[List[DishRecommendation], NutritionAdvice, List[Allergen], List[str]]:
        if exclude_dish_ids is None:
            exclude_dish_ids = []
        
        all_allergens = set()
        all_disliked_ingredients = set()
        all_tastes = set()
        all_cuisines = set()
        users_list = []
        
        for user_id in user_ids:
            user = self.users.get(user_id)
            if user:
                users_list.append(user)
                all_allergens.update(user.allergens)
                all_disliked_ingredients.update(user.preferences.disliked_ingredients)
                all_tastes.update(user.preferences.taste_preferences)
                all_cuisines.update(user.preferences.cuisine_preferences)
        
        allergen_free_dishes = self.kg.get_allergen_free_dishes(list(all_allergens))
        safe_dishes = self.kg.get_dishes_without_ingredients(list(all_disliked_ingredients))
        valid_dishes = allergen_free_dishes & safe_dishes
        
        individual_recs = []
        for user_id in user_ids:
            recs, _, _ = self.get_personalized_recommendations(
                user_id, current_season, exclude_dish_ids, top_n=20
            )
            individual_recs.append({r.dish_id: r.score for r in recs})
        
        combined_scores = defaultdict(float)
        for rec_dict in individual_recs:
            for dish_id, score in rec_dict.items():
                if dish_id in valid_dishes:
                    combined_scores[dish_id] += score / len(individual_recs)
        
        group_scores = defaultdict(float)
        group_reasons = defaultdict(list)
        
        for dish_id, avg_score in combined_scores.items():
            group_scores[dish_id] = avg_score * 0.5
            group_reasons[dish_id].append("符合团队成员偏好")
        
        frequent_combinations = self.ar.get_frequent_combinations(k=3, top_n=5)
        for itemset, support in frequent_combinations:
            nutritious_dishes = [d for d in itemset if self.nutrition_calculator.has_nutritional_value(self.dishes[d])]
            for dish_id in nutritious_dishes:
                if dish_id in valid_dishes:
                    group_scores[dish_id] += support * 0.2
                    if support > 0.2:
                        group_reasons[dish_id].append("热门组合菜品")
        
        num_dishes = max(3, int(len(user_ids) * dishes_per_person))
        
        candidate_dishes = sorted(group_scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = self._select_balanced_and_conflict_free(
            candidate_dishes,
            num_dishes,
            valid_dishes,
            balance_types or []
        )
        
        selected_ids = [d_id for d_id, _ in selected]
        dish_tastes = {d_id: self.dish_taste_map.get(d_id, []) for d_id in selected_ids}
        conflicts = self.conflict_detector.detect_conflicts(dish_tastes)
        taste_conflicts = [
            TasteConflict(
                conflict_tastes=(c["taste1"], c["taste2"]),
                severity=c["severity"],
                description=c["description"]
            )
            for c in conflicts
        ]
        
        recommendations = []
        for dish_id, score in selected:
            dish = self.dishes[dish_id]
            reason = " + ".join(group_reasons.get(dish_id, ["综合推荐"]))
            recommendations.append(DishRecommendation(
                dish_id=dish_id,
                dish_name=dish.name,
                score=min(score, 1.0),
                reason=reason,
                matched_features=[]
            ))
        
        selected_dish_ids = [r.dish_id for r in recommendations]
        nutrition_advice = self.get_personalized_nutrition_advice(
            users_list,
            selected_dish_ids,
            balance_types or []
        )
        nutrition_advice.conflicts_found = taste_conflicts
        
        seasonal_recommendations = [
            self.dishes[d].name for d in self.kg.get_seasonal_dishes(current_season)
            if d in valid_dishes
        ][:5]
        
        return recommendations, nutrition_advice, list(all_allergens), seasonal_recommendations
    
    def _select_balanced_and_conflict_free(
        self,
        candidate_dishes: List[Tuple[str, float]],
        num_dishes: int,
        valid_dishes: set,
        balance_types: List[str]
    ) -> List[Tuple[str, float]]:
        meat_tags = ["牛肉", "猪肉", "鸡肉", "鱼", "虾", "鸭", "羊"]
        
        meat_dishes = []
        veg_dishes = []
        
        for dish_id, score in candidate_dishes:
            if dish_id not in valid_dishes:
                continue
            dish = self.dishes[dish_id]
            is_meat = any(ing in dish.ingredients for ing in meat_tags)
            if is_meat:
                meat_dishes.append((dish_id, score))
            else:
                veg_dishes.append((dish_id, score))
        
        if "meat_vegetable" in balance_types:
            num_meat = min(len(meat_dishes), num_dishes // 2)
            num_veg = num_dishes - num_meat
            
            meat_candidates = meat_dishes[:num_meat * 2]
            veg_candidates = veg_dishes[:num_veg * 2]
        else:
            meat_candidates = meat_dishes
            veg_candidates = veg_dishes
        
        selected = []
        selected_ids = []
        
        combined_candidates = []
        if "meat_vegetable" in balance_types:
            for i in range(max(num_meat, num_veg)):
                if i < len(meat_candidates):
                    combined_candidates.append(meat_candidates[i])
                if i < len(veg_candidates):
                    combined_candidates.append(veg_candidates[i])
        else:
            combined_candidates = candidate_dishes
        
        for dish_id, score in combined_candidates:
            if len(selected) >= num_dishes:
                break
            
            test_selected = selected_ids + [dish_id]
            test_tastes = {d: self.dish_taste_map.get(d, []) for d in test_selected}
            
            if self.conflict_detector.has_severe_conflict(test_tastes):
                continue
            
            selected.append((dish_id, score))
            selected_ids.append(dish_id)
        
        if len(selected) < num_dishes:
            for dish_id, score in combined_candidates:
                if len(selected) >= num_dishes:
                    break
                if dish_id not in selected_ids:
                    selected.append((dish_id, score))
                    selected_ids.append(dish_id)
        
        return selected
    
    def get_personalized_nutrition_advice(
        self,
        users: List[User],
        dish_ids: List[str],
        balance_types: List[str]
    ) -> NutritionAdvice:
        from models.schemas import PersonalizedNutritionTarget
        
        total_nutrition = {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbohydrates": 0,
            "fiber": 0
        }
        
        for dish_id in dish_ids:
            if dish_id in self.dishes:
                dish = self.dishes[dish_id]
                for key in total_nutrition:
                    total_nutrition[key] += getattr(dish.nutrition, key)
        
        if not users:
            return NutritionAdvice(
                advice="当前菜品搭配",
                suggestion_dish_ids=[],
                nutrition_gap={},
                current_nutrition=total_nutrition
            )
        
        avg_target = self._calculate_average_target(users, len(dish_ids) / max(len(users), 1))
        
        nutrition_gap, status = self.nutrition_calculator.analyze_nutrition(
            total_nutrition,
            avg_target
        )
        
        avg_bmi = 0
        bmi_categories = []
        for user in users:
            bmi = user.health_data.bmi or self.nutrition_calculator.calculate_bmi(
                user.health_data.weight or 65.0,
                user.health_data.height or 170.0
            )
            avg_bmi += bmi
            bmi_categories.append(self.nutrition_calculator.get_bmi_category(bmi))
        
        avg_bmi = avg_bmi / len(users) if users else 0
        bmi_category = self.nutrition_calculator.get_bmi_category(avg_bmi)
        
        advice = self.nutrition_calculator.generate_nutrition_advice(
            status,
            nutrition_gap,
            bmi_category
        )
        
        suggestions = []
        if status.get("protein") in ["偏低", "严重不足"]:
            high_protein = self.kg.get_dishes_by_nutrition_tag("high_protein")
            for dp in high_protein:
                if dp not in dish_ids:
                    suggestions.append(dp)
                    break
        
        if status.get("fiber") in ["偏低", "严重不足"]:
            high_fiber = self.kg.get_dishes_by_nutrition_tag("high_fiber")
            for df in high_fiber:
                if df not in dish_ids:
                    suggestions.append(df)
                    break
        
        return NutritionAdvice(
            advice=advice,
            suggestion_dish_ids=list(set(suggestions))[:3],
            nutrition_gap=nutrition_gap,
            nutrition_target=avg_target,
            current_nutrition=total_nutrition,
            bmi_category=bmi_category
        )
    
    def _calculate_average_target(self, users: List[User], meal_multiplier: float) -> PersonalizedNutritionTarget:
        from models.schemas import PersonalizedNutritionTarget
        
        if not users:
            return PersonalizedNutritionTarget(
                calories=800, protein=30, fat=25, carbohydrates=80, fiber=10
            )
        
        targets = []
        for user in users:
            target = self.nutrition_calculator.get_nutrition_target(user, meal_count=int(meal_multiplier) or 1)
            targets.append(target)
        
        avg_calories = sum(t.calories for t in targets) / len(targets)
        avg_protein = sum(t.protein for t in targets) / len(targets)
        avg_fat = sum(t.fat for t in targets) / len(targets)
        avg_carbs = sum(t.carbohydrates for t in targets) / len(targets)
        avg_fiber = sum(t.fiber for t in targets) / len(targets)
        
        return PersonalizedNutritionTarget(
            calories=avg_calories,
            protein=avg_protein,
            fat=avg_fat,
            carbohydrates=avg_carbs,
            fiber=avg_fiber
        )
    
    def get_nutrition_advice(self, dish_ids: List[str], balance_types: List[str]) -> NutritionAdvice:
        return self.get_personalized_nutrition_advice([], dish_ids, balance_types)
    
    def get_associated_dishes_for_cart(
        self,
        cart_dish_ids: List[str],
        user_id: Optional[str] = None,
        top_n: int = 5
    ) -> List[DishRecommendation]:
        associations = self.ar.get_recommendations_for_cart(cart_dish_ids, top_n=top_n * 3)
        
        filtered_associations = []
        for dish_id, confidence, reason in associations:
            if self.nutrition_calculator.has_nutritional_value(self.dishes[dish_id]):
                filtered_associations.append((dish_id, confidence, reason))
        
        if user_id:
            user = self.users.get(user_id)
            if user:
                allergen_free = self.kg.get_allergen_free_dishes(user.allergens)
                safe_dishes = self.kg.get_dishes_without_ingredients(user.preferences.disliked_ingredients)
                filtered_associations = [
                    (d, s, r) for d, s, r in filtered_associations
                    if d in allergen_free and d in safe_dishes
                ]
        
        cart_tastes = {d: self.dish_taste_map.get(d, []) for d in cart_dish_ids}
        
        final_recommendations = []
        for dish_id, confidence, reason in filtered_associations[:top_n * 2]:
            test_tastes = dict(cart_tastes)
            test_tastes[dish_id] = self.dish_taste_map.get(dish_id, [])
            
            if self.conflict_detector.has_severe_conflict(test_tastes):
                adjusted_confidence = confidence * 0.6
                final_recommendations.append((dish_id, adjusted_confidence, reason + "（注意口味冲突）"))
            else:
                final_recommendations.append((dish_id, confidence, reason))
        
        final_recommendations.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for dish_id, confidence, reason in final_recommendations[:top_n]:
            dish = self.dishes[dish_id]
            recommendations.append(DishRecommendation(
                dish_id=dish_id,
                dish_name=dish.name,
                score=confidence,
                reason=reason,
                matched_features=["关联搭配", "营养优选"]
            ))
        
        return recommendations
    
    def get_similar_dishes(self, dish_id: str, user_id: Optional[str] = None, top_n: int = 5) -> List[DishRecommendation]:
        similar = self.kg.get_similar_dishes(dish_id, top_n=top_n * 2)
        cf_similar = dict(self.cf.get_similar_dishes(dish_id, k=top_n * 2))
        
        combined = []
        for d_id, kg_score in similar:
            cf_score = cf_similar.get(d_id, 0)
            total_score = kg_score * 0.6 + cf_score * 0.4
            combined.append((d_id, total_score))
        
        combined.sort(key=lambda x: x[1], reverse=True)
        
        if user_id:
            user = self.users.get(user_id)
            if user:
                allergen_free = self.kg.get_allergen_free_dishes(user.allergens)
                combined = [(d, s) for d, s in combined if d in allergen_free]
        
        recommendations = []
        for d_id, score in combined[:top_n]:
            dish = self.dishes[d_id]
            relations = self.kg.explain_dish_relation(dish_id, d_id)
            reason = "、".join(relations) if relations else "菜品相似"
            
            if self.nutrition_calculator.has_nutritional_value(dish):
                reason += "（营养丰富）"
            
            recommendations.append(DishRecommendation(
                dish_id=d_id,
                dish_name=dish.name,
                score=score,
                reason=reason,
                matched_features=["相似菜品"]
            ))
        
        return recommendations
    
    def _season_text(self, season: Season) -> str:
        season_map = {
            Season.SPRING: "春季",
            Season.SUMMER: "夏季",
            Season.AUTUMN: "秋季",
            Season.WINTER: "冬季"
        }
        return season_map.get(season, "")
