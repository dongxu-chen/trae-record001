from typing import Dict, List, Set, Tuple, Optional
from models.schemas import Allergen, AllergenKnowledge, Dish, User


class AllergyKnowledgeBase:
    def __init__(self):
        self.knowledge_base = self._build_knowledge_base()
        self.ingredient_to_allergen = self._build_ingredient_mapping()
    
    def _build_knowledge_base(self) -> Dict[Allergen, AllergenKnowledge]:
        knowledge = {}
        
        knowledge[Allergen.PEANUT] = AllergenKnowledge(
            allergen=Allergen.PEANUT,
            common_names=["花生", "花生米", "落花生", "长生果"],
            related_ingredients=["花生酱", "花生油", "花生碎", "花生粉", "炒花生"],
            cross_reactivity=[Allergen.NUTS],
            severity_level="high",
            description="花生是最常见的食物过敏源之一，可能引起严重过敏反应",
            avoidance_tips=[
                "避免食用含花生成分的食品",
                "注意食品包装上的'可能含有花生'警示",
                "中式菜肴中常使用花生调味，需特别注意"
            ]
        )
        
        knowledge[Allergen.SHELLFISH] = AllergenKnowledge(
            allergen=Allergen.SHELLFISH,
            common_names=["虾", "蟹", "龙虾", "小龙虾", "皮皮虾", "对虾", "基围虾"],
            related_ingredients=["虾仁", "虾米", "虾皮", "蟹肉", "蟹黄", "虾酱", "蚝油"],
            cross_reactivity=[Allergen.MOLLUSCS],
            severity_level="high",
            description="甲壳类海鲜过敏，成人中较为常见",
            avoidance_tips=[
                "避免所有甲壳类海鲜",
                "注意海鲜酱油、XO酱等调味品",
                "避免在海鲜餐厅就餐以防交叉污染"
            ]
        )
        
        knowledge[Allergen.FISH] = AllergenKnowledge(
            allergen=Allergen.FISH,
            common_names=["鱼", "草鱼", "鲈鱼", "鲤鱼", "鲫鱼", "黑鱼", "三文鱼", "金枪鱼"],
            related_ingredients=["鱼丸", "鱼豆腐", "鱼糜", "鱼露", "鱼肉", "鱼片"],
            cross_reactivity=[],
            severity_level="medium",
            description="鱼类过敏，注意不同鱼种可能有交叉反应",
            avoidance_tips=[
                "避免食用所有鱼类",
                "注意鱼露、 Worcestershire酱等调味品",
                "泰国菜、越南菜中常用鱼露调味"
            ]
        )
        
        knowledge[Allergen.MILK] = AllergenKnowledge(
            allergen=Allergen.MILK,
            common_names=["牛奶", "奶", "牛乳"],
            related_ingredients=["奶酪", "芝士", "黄油", "奶油", "酸奶", "奶粉", "炼乳", "奶精"],
            cross_reactivity=[],
            severity_level="medium",
            description="牛奶过敏，常见于儿童",
            avoidance_tips=[
                "选择植物奶替代（豆奶、燕麦奶等）",
                "注意面包、蛋糕中的牛奶成分",
                "咖啡、奶茶中的奶精可能含牛奶成分"
            ]
        )
        
        knowledge[Allergen.EGG] = AllergenKnowledge(
            allergen=Allergen.EGG,
            common_names=["鸡蛋", "蛋", "鸡子"],
            related_ingredients=["蛋清", "蛋黄", "鸡蛋液", "蛋羹", "蛋花", "鹌鹑蛋", "皮蛋"],
            cross_reactivity=[],
            severity_level="medium",
            description="鸡蛋过敏，常见于儿童",
            avoidance_tips=[
                "注意糕点、面条中的鸡蛋成分",
                "蛋黄酱、沙拉酱可能含鸡蛋",
                "中餐中的蛋花汤、芙蓉蛋需避免"
            ]
        )
        
        knowledge[Allergen.WHEAT] = AllergenKnowledge(
            allergen=Allergen.WHEAT,
            common_names=["小麦", "面粉", "白面"],
            related_ingredients=["面条", "面包", "馒头", "饺子皮", "包子", "饼干", "蛋糕", "面筋"],
            cross_reactivity=[],
            severity_level="medium",
            description="小麦过敏，包括麸质过敏",
            avoidance_tips=[
                "选择米粉、玉米粉替代",
                "注意酱油、酱料中的小麦成分",
                "避免食用小麦制品勾芡的菜肴"
            ]
        )
        
        knowledge[Allergen.SOY] = AllergenKnowledge(
            allergen=Allergen.SOY,
            common_names=["大豆", "黄豆", "豆腐"],
            related_ingredients=["酱油", "豆浆", "豆皮", "豆干", "腐乳", "味噌", "毛豆"],
            cross_reactivity=[],
            severity_level="low",
            description="大豆过敏，亚洲人中较为常见",
            avoidance_tips=[
                "注意所有豆制品",
                "酱油是中餐最常见的大豆来源",
                "选择无酱油调味的菜品"
            ]
        )
        
        knowledge[Allergen.NUTS] = AllergenKnowledge(
            allergen=Allergen.NUTS,
            common_names=["坚果", "杏仁", "核桃", "腰果", "开心果", "榛子", "板栗"],
            related_ingredients=["坚果碎", "杏仁粉", "核桃露", "芝麻酱", "坚果酱"],
            cross_reactivity=[Allergen.PEANUT],
            severity_level="high",
            description="树坚果过敏，可能与花生交叉反应",
            avoidance_tips=[
                "避免所有坚果类食品",
                "注意糕点、冰淇淋中的坚果成分",
                "五仁月饼、坚果沙拉需特别注意"
            ]
        )
        
        knowledge[Allergen.SESAME] = AllergenKnowledge(
            allergen=Allergen.SESAME,
            common_names=["芝麻", "白芝麻", "黑芝麻"],
            related_ingredients=["芝麻油", "香油", "芝麻酱", "芝麻糊"],
            cross_reactivity=[],
            severity_level="medium",
            description="芝麻过敏，亚洲饮食中常见",
            avoidance_tips=[
                "避免芝麻油/香油调味的菜品",
                "注意撒有芝麻的面点和菜肴",
                "芝麻酱是火锅蘸料的常见成分"
            ]
        )
        
        return knowledge
    
    def _build_ingredient_mapping(self) -> Dict[str, Allergen]:
        mapping = {}
        for allergen, knowledge in self.knowledge_base.items():
            for name in knowledge.common_names:
                mapping[name] = allergen
            for ingredient in knowledge.related_ingredients:
                mapping[ingredient] = allergen
        return mapping
    
    def auto_detect_allergens(self, dish: Dish) -> List[Allergen]:
        detected = set(dish.allergens)
        
        all_text = dish.name + " " + dish.description + " " + " ".join(dish.ingredients)
        
        for keyword, allergen in self.ingredient_to_allergen.items():
            if keyword in all_text:
                detected.add(allergen)
        
        return list(detected)
    
    def label_dish_allergens(self, dish: Dish) -> Tuple[List[Allergen], List[str]]:
        allergens = self.auto_detect_allergens(dish)
        labels = []
        
        for allergen in allergens:
            knowledge = self.knowledge_base.get(allergen)
            if knowledge:
                matched = []
                for name in knowledge.common_names:
                    if name in dish.name or name in " ".join(dish.ingredients):
                        matched.append(name)
                if matched:
                    labels.append(f"{allergen.value}（含有：{', '.join(matched)}）")
                else:
                    labels.append(allergen.value)
        
        return allergens, labels
    
    def get_allergen_info(self, allergen: Allergen) -> Optional[AllergenKnowledge]:
        return self.knowledge_base.get(allergen)
    
    def get_user_allergen_warnings(self, user: User, dish: Dish) -> List[Dict]:
        warnings = []
        user_allergens = set(user.allergens)
        dish_allergens = set(self.auto_detect_allergens(dish))
        
        conflicts = user_allergens & dish_allergens
        
        for allergen in conflicts:
            knowledge = self.get_allergen_info(allergen)
            if knowledge:
                warnings.append({
                    "allergen": allergen,
                    "severity": knowledge.severity_level,
                    "description": knowledge.description,
                    "tips": knowledge.avoidance_tips
                })
        
        return warnings
    
    def get_cross_reactive_allergens(self, allergen: Allergen) -> List[Allergen]:
        knowledge = self.get_allergen_info(allergen)
        if knowledge:
            return knowledge.cross_reactivity
        return []
    
    def check_menu_safety(self, user: User, dishes: List[Dish]) -> Dict:
        safe_dishes = []
        risky_dishes = []
        high_risk_dishes = []
        
        for dish in dishes:
            warnings = self.get_user_allergen_warnings(user, dish)
            if not warnings:
                safe_dishes.append({
                    "dish_id": dish.dish_id,
                    "name": dish.name,
                    "status": "safe"
                })
            else:
                has_high_risk = any(w["severity"] == "high" for w in warnings)
                dish_info = {
                    "dish_id": dish.dish_id,
                    "name": dish.name,
                    "warnings": warnings,
                    "status": "risky"
                }
                if has_high_risk:
                    high_risk_dishes.append(dish_info)
                else:
                    risky_dishes.append(dish_info)
        
        return {
            "safe_count": len(safe_dishes),
            "risky_count": len(risky_dishes),
            "high_risk_count": len(high_risk_dishes),
            "safe_dishes": safe_dishes,
            "risky_dishes": risky_dishes,
            "high_risk_dishes": high_risk_dishes
        }
    
    def get_alternative_dishes(
        self,
        user: User,
        unsafe_dish: Dish,
        all_dishes: Dict[str, Dish],
        top_n: int = 3
    ) -> List[Dish]:
        alternatives = []
        
        for dish_id, dish in all_dishes.items():
            if dish_id == unsafe_dish.dish_id:
                continue
            
            warnings = self.get_user_allergen_warnings(user, dish)
            if warnings:
                continue
            
            similarity = 0
            if dish.cuisine == unsafe_dish.cuisine:
                similarity += 0.3
            
            common_tastes = set(dish.taste_tags) & set(unsafe_dish.taste_tags)
            similarity += len(common_tastes) * 0.1
            
            price_diff = abs(dish.price - unsafe_dish.price)
            if price_diff <= 20:
                similarity += 0.2
            elif price_diff <= 50:
                similarity += 0.1
            
            if similarity >= 0.3:
                alternatives.append((dish, similarity))
        
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in alternatives[:top_n]]
    
    def generate_allergen_legend(self) -> Dict[str, List]:
        legend = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for allergen, knowledge in self.knowledge_base.items():
            legend[knowledge.severity_level].append({
                "code": allergen.value,
                "name": allergen.value,
                "description": knowledge.description
            })
        
        return legend
