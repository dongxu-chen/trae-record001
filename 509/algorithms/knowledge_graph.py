import networkx as nx
from typing import Dict, List, Tuple, Set, Optional
from models.schemas import User, Dish, Allergen, NutritionInfo, Season
from collections import defaultdict


class DishKnowledgeGraph:
    def __init__(self, dishes: Dict[str, Dish]):
        self.dishes = dishes
        self.graph = nx.DiGraph()
        self._build_graph()
    
    def _build_graph(self):
        for dish_id, dish in self.dishes.items():
            self.graph.add_node(dish_id, type="dish", name=dish.name, cuisine=dish.cuisine)
            
            cuisine_node = f"cuisine:{dish.cuisine}"
            if not self.graph.has_node(cuisine_node):
                self.graph.add_node(cuisine_node, type="cuisine", name=dish.cuisine)
            self.graph.add_edge(dish_id, cuisine_node, relation="belongs_to_cuisine")
            self.graph.add_edge(cuisine_node, dish_id, relation="contains_dish")
            
            for taste in dish.taste_tags:
                taste_node = f"taste:{taste}"
                if not self.graph.has_node(taste_node):
                    self.graph.add_node(taste_node, type="taste", name=taste)
                self.graph.add_edge(dish_id, taste_node, relation="has_taste")
                self.graph.add_edge(taste_node, dish_id, relation="taste_of")
            
            for ingredient in dish.ingredients:
                ingredient_node = f"ingredient:{ingredient}"
                if not self.graph.has_node(ingredient_node):
                    self.graph.add_node(ingredient_node, type="ingredient", name=ingredient)
                self.graph.add_edge(dish_id, ingredient_node, relation="contains_ingredient")
                self.graph.add_edge(ingredient_node, dish_id, relation="ingredient_of")
            
            if dish.season:
                season_node = f"season:{dish.season}"
                if not self.graph.has_node(season_node):
                    self.graph.add_node(season_node, type="season", name=dish.season)
                self.graph.add_edge(dish_id, season_node, relation="best_in_season")
                self.graph.add_edge(season_node, dish_id, relation="seasonal_dish")
            
            for allergen in dish.allergens:
                allergen_node = f"allergen:{allergen}"
                if not self.graph.has_node(allergen_node):
                    self.graph.add_node(allergen_node, type="allergen", name=allergen)
                self.graph.add_edge(dish_id, allergen_node, relation="contains_allergen")
                self.graph.add_edge(allergen_node, dish_id, relation="allergen_in")
        
        self._add_nutrition_relations()
        self._add_dish_similarity_edges()
    
    def _add_nutrition_relations(self):
        nutrition_levels = {
            "high_protein": (25, float('inf'), "protein"),
            "low_calorie": (0, 250, "calories"),
            "high_fiber": (3, float('inf'), "fiber"),
            "low_fat": (0, 10, "fat"),
        }
        
        for dish_id, dish in self.dishes.items():
            for label, (min_val, max_val, attr) in nutrition_levels.items():
                value = getattr(dish.nutrition, attr)
                if min_val <= value <= max_val:
                    nutri_node = f"nutrition:{label}"
                    if not self.graph.has_node(nutri_node):
                        self.graph.add_node(nutri_node, type="nutrition", name=label)
                    self.graph.add_edge(dish_id, nutri_node, relation="has_nutrition_tag")
                    self.graph.add_edge(nutri_node, dish_id, relation="nutrition_tag_of")
    
    def _add_dish_similarity_edges(self):
        dish_ids = list(self.dishes.keys())
        for i, dish1_id in enumerate(dish_ids):
            for dish2_id in dish_ids[i+1:]:
                dish1 = self.dishes[dish1_id]
                dish2 = self.dishes[dish2_id]
                
                similarity = 0
                
                if dish1.cuisine == dish2.cuisine:
                    similarity += 0.3
                
                common_tastes = set(dish1.taste_tags) & set(dish2.taste_tags)
                similarity += len(common_tastes) * 0.15
                
                common_ingredients = set(dish1.ingredients) & set(dish2.ingredients)
                similarity += len(common_ingredients) * 0.1
                
                if similarity >= 0.4:
                    self.graph.add_edge(dish1_id, dish2_id, relation="similar_to", weight=similarity)
                    self.graph.add_edge(dish2_id, dish1_id, relation="similar_to", weight=similarity)
    
    def get_seasonal_dishes(self, season: Season) -> List[str]:
        season_node = f"season:{season}"
        if not self.graph.has_node(season_node):
            return []
        
        dishes = []
        for neighbor in self.graph.neighbors(season_node):
            if self.graph.nodes[neighbor].get("type") == "dish":
                dishes.append(neighbor)
        return dishes
    
    def get_dishes_by_cuisine(self, cuisine: str) -> List[str]:
        cuisine_node = f"cuisine:{cuisine}"
        if not self.graph.has_node(cuisine_node):
            return []
        
        dishes = []
        for neighbor in self.graph.neighbors(cuisine_node):
            if self.graph.nodes[neighbor].get("type") == "dish":
                dishes.append(neighbor)
        return dishes
    
    def get_dishes_by_taste(self, taste: str) -> List[str]:
        taste_node = f"taste:{taste}"
        if not self.graph.has_node(taste_node):
            return []
        
        dishes = []
        for neighbor in self.graph.neighbors(taste_node):
            if self.graph.nodes[neighbor].get("type") == "dish":
                dishes.append(neighbor)
        return dishes
    
    def get_dishes_by_nutrition_tag(self, tag: str) -> List[str]:
        nutri_node = f"nutrition:{tag}"
        if not self.graph.has_node(nutri_node):
            return []
        
        dishes = []
        for neighbor in self.graph.neighbors(nutri_node):
            if self.graph.nodes[neighbor].get("type") == "dish":
                dishes.append(neighbor)
        return dishes
    
    def get_similar_dishes(self, dish_id: str, top_n: int = 5) -> List[Tuple[str, float]]:
        if not self.graph.has_node(dish_id):
            return []
        
        similar = []
        for neighbor, edge_data in self.graph[dish_id].items():
            if edge_data.get("relation") == "similar_to":
                weight = edge_data.get("weight", 0)
                similar.append((neighbor, weight))
        
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar[:top_n]
    
    def get_allergen_free_dishes(self, allergens: List[Allergen]) -> Set[str]:
        allergen_dishes = set()
        for allergen in allergens:
            allergen_node = f"allergen:{allergen}"
            if self.graph.has_node(allergen_node):
                for neighbor in self.graph.neighbors(allergen_node):
                    if self.graph.nodes[neighbor].get("type") == "dish":
                        allergen_dishes.add(neighbor)
        
        all_dishes = set(self.dishes.keys())
        return all_dishes - allergen_dishes
    
    def get_dishes_with_ingredients(self, ingredients: List[str]) -> List[str]:
        dish_counts = defaultdict(int)
        for ingredient in ingredients:
            ingredient_node = f"ingredient:{ingredient}"
            if self.graph.has_node(ingredient_node):
                for neighbor in self.graph.neighbors(ingredient_node):
                    if self.graph.nodes[neighbor].get("type") == "dish":
                        dish_counts[neighbor] += 1
        
        result = [(dish_id, count) for dish_id, count in dish_counts.items()]
        result.sort(key=lambda x: x[1], reverse=True)
        return [dish_id for dish_id, _ in result]
    
    def get_dishes_without_ingredients(self, ingredients: List[str]) -> Set[str]:
        ingredient_dishes = set()
        for ingredient in ingredients:
            ingredient_node = f"ingredient:{ingredient}"
            if self.graph.has_node(ingredient_node):
                for neighbor in self.graph.neighbors(ingredient_node):
                    if self.graph.nodes[neighbor].get("type") == "dish":
                        ingredient_dishes.add(neighbor)
        
        all_dishes = set(self.dishes.keys())
        return all_dishes - ingredient_dishes
    
    def recommend_based_on_preferences(self, tastes: List[str] = None, cuisines: List[str] = None,
                                         disliked_ingredients: List[str] = None,
                                         allergens: List[Allergen] = None,
                                         top_n: int = 10) -> List[Tuple[str, float]]:
        scores = defaultdict(float)
        
        if tastes:
            for taste in tastes:
                dishes = self.get_dishes_by_taste(taste)
                for dish_id in dishes:
                    scores[dish_id] += 0.2
        
        if cuisines:
            for cuisine in cuisines:
                dishes = self.get_dishes_by_cuisine(cuisine)
                for dish_id in dishes:
                    scores[dish_id] += 0.25
        
        valid_dishes = set(scores.keys())
        
        if disliked_ingredients:
            safe_dishes = self.get_dishes_without_ingredients(disliked_ingredients)
            valid_dishes = valid_dishes & safe_dishes
        
        if allergens:
            safe_dishes = self.get_allergen_free_dishes(allergens)
            valid_dishes = valid_dishes & safe_dishes
        
        result = [(dish_id, scores[dish_id]) for dish_id in valid_dishes]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:top_n]
    
    def get_nutrition_balanced_combination(self, dish_ids: List[str], 
                                            target_calories: float = None,
                                            balance_types: List[str] = None) -> Tuple[Dict[str, float], List[str]]:
        if not dish_ids:
            return {}, []
        
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
        
        suggestions = []
        advice = []
        
        if "nutrition" in (balance_types or []):
            if total_nutrition["protein"] < 50:
                high_protein = self.get_dishes_by_nutrition_tag("high_protein")
                for dp in high_protein:
                    if dp not in dish_ids:
                        suggestions.append(dp)
                        break
                advice.append("建议增加高蛋白菜品")
            
            if total_nutrition["fiber"] < 10:
                high_fiber = self.get_dishes_by_nutrition_tag("high_fiber")
                for df in high_fiber:
                    if df not in dish_ids:
                        suggestions.append(df)
                        break
                advice.append("建议增加高纤维菜品")
        
        if target_calories and total_nutrition["calories"] > target_calories:
            low_calorie = self.get_dishes_by_nutrition_tag("low_calorie")
            suggestions.extend([d for d in low_calorie if d not in dish_ids])
            advice.append("当前热量偏高，建议选择低卡菜品")
        
        return total_nutrition, list(set(suggestions))[:3]
    
    def get_dish_allergens(self, dish_id: str) -> List[Allergen]:
        if dish_id not in self.dishes:
            return []
        return self.dishes[dish_id].allergens
    
    def explain_dish_relation(self, dish1_id: str, dish2_id: str) -> List[str]:
        explanations = []
        
        if dish1_id not in self.dishes or dish2_id not in self.dishes:
            return explanations
        
        dish1 = self.dishes[dish1_id]
        dish2 = self.dishes[dish2_id]
        
        if dish1.cuisine == dish2.cuisine:
            explanations.append(f"同属于{dish1.cuisine}")
        
        common_tastes = set(dish1.taste_tags) & set(dish2.taste_tags)
        if common_tastes:
            explanations.append(f"口味相似: {', '.join(common_tastes)}")
        
        common_ingredients = set(dish1.ingredients) & set(dish2.ingredients)
        if common_ingredients:
            explanations.append(f"都包含: {', '.join(common_ingredients)}")
        
        return explanations
