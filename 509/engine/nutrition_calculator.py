from typing import Dict, Optional, Tuple
from models.schemas import User, ActivityLevel, PersonalizedNutritionTarget, Dish


class PersonalizedNutritionCalculator:
    def __init__(self):
        self.activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9,
        }
    
    def calculate_bmi(self, weight: float, height: float) -> float:
        if height <= 0:
            return 0.0
        height_m = height / 100.0
        return round(weight / (height_m * height_m), 1)
    
    def get_bmi_category(self, bmi: float) -> str:
        if bmi < 18.5:
            return "偏瘦"
        elif 18.5 <= bmi < 24:
            return "正常"
        elif 24 <= bmi < 28:
            return "超重"
        else:
            return "肥胖"
    
    def calculate_bmr(self, user: User) -> float:
        weight = user.health_data.weight or 65.0
        height = user.health_data.height or 170.0
        age = user.age or 30
        gender = user.gender or "male"
        
        if gender == "male":
            bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
        
        return round(bmr, 0)
    
    def calculate_tdee(self, user: User) -> float:
        bmr = self.calculate_bmr(user)
        activity_level = user.health_data.activity_level
        multiplier = self.activity_multipliers.get(activity_level, 1.55)
        return round(bmr * multiplier, 0)
    
    def get_nutrition_target(self, user: User, meal_count: int = 1) -> PersonalizedNutritionTarget:
        tdee = self.calculate_tdee(user)
        bmi = user.health_data.bmi or self.calculate_bmi(
            user.health_data.weight or 65.0,
            user.health_data.height or 170.0
        )
        bmi_category = self.get_bmi_category(bmi)
        
        target_calories = tdee / 3 * meal_count
        
        if bmi_category == "超重" or bmi_category == "肥胖":
            target_calories *= 0.85
        elif bmi_category == "偏瘦":
            target_calories *= 1.15
        
        if user.health_data.target_weight and user.health_data.weight:
            if user.health_data.target_weight < user.health_data.weight:
                target_calories *= 0.9
            elif user.health_data.target_weight > user.health_data.weight:
                target_calories *= 1.1
        
        if "糖尿病" in user.health_data.health_conditions:
            target_calories *= 0.9
        
        if "高血压" in user.health_data.health_conditions:
            sodium_limit = 1500
        else:
            sodium_limit = 2300
        
        activity_level = user.health_data.activity_level
        if activity_level in [ActivityLevel.ACTIVE, ActivityLevel.VERY_ACTIVE]:
            protein_ratio = 0.3
            carb_ratio = 0.45
        elif activity_level == ActivityLevel.SEDENTARY:
            protein_ratio = 0.25
            carb_ratio = 0.4
        else:
            protein_ratio = 0.25
            carb_ratio = 0.5
        
        fat_ratio = 1.0 - protein_ratio - carb_ratio
        
        protein_cal = target_calories * protein_ratio
        fat_cal = target_calories * fat_ratio
        carb_cal = target_calories * carb_ratio
        
        protein_g = protein_cal / 4
        fat_g = fat_cal / 9
        carb_g = carb_cal / 4
        
        if bmi_category == "偏瘦":
            protein_g *= 1.2
        
        fiber_g = max(25.0, target_calories / 1000 * 14) / 3 * meal_count
        
        return PersonalizedNutritionTarget(
            calories=round(target_calories, 0),
            protein=round(protein_g, 1),
            fat=round(fat_g, 1),
            carbohydrates=round(carb_g, 1),
            fiber=round(fiber_g, 1)
        )
    
    def analyze_nutrition(
        self,
        current_nutrition: Dict[str, float],
        target: PersonalizedNutritionTarget
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        nutrition_gap = {}
        status = {}
        
        for nutrient in ["calories", "protein", "fat", "carbohydrates", "fiber"]:
            current = current_nutrition.get(nutrient, 0)
            target_val = getattr(target, nutrient, 0)
            
            if target_val > 0:
                ratio = current / target_val
                nutrition_gap[nutrient] = round(target_val - current, 1)
                
                if ratio < 0.6:
                    status[nutrient] = "严重不足"
                elif ratio < 0.8:
                    status[nutrient] = "偏低"
                elif ratio > 1.3:
                    status[nutrient] = "超标"
                elif ratio > 1.1:
                    status[nutrient] = "偏高"
                else:
                    status[nutrient] = "正常"
            else:
                status[nutrient] = "正常"
        
        return nutrition_gap, status
    
    def generate_nutrition_advice(
        self,
        status: Dict[str, str],
        nutrition_gap: Dict[str, float],
        bmi_category: str
    ) -> str:
        advice_parts = []
        
        if bmi_category == "超重":
            advice_parts.append("您的BMI处于超重范围，建议控制热量摄入")
        elif bmi_category == "肥胖":
            advice_parts.append("您的BMI处于肥胖范围，建议减少高热量食物")
        elif bmi_category == "偏瘦":
            advice_parts.append("您的BMI偏瘦，建议适当增加蛋白质摄入")
        
        if status.get("protein") == "严重不足":
            advice_parts.append(f"蛋白质严重不足（还差{nutrition_gap['protein']:.1f}g），建议增加高蛋白菜品")
        elif status.get("protein") == "偏低":
            advice_parts.append(f"蛋白质偏低（还差{nutrition_gap['protein']:.1f}g），建议补充蛋白质")
        
        if status.get("fiber") == "严重不足":
            advice_parts.append(f"膳食纤维严重不足（还差{nutrition_gap['fiber']:.1f}g），建议增加蔬果类菜品")
        elif status.get("fiber") == "偏低":
            advice_parts.append(f"膳食纤维偏低（还差{nutrition_gap['fiber']:.1f}g），建议多吃蔬菜")
        
        if status.get("calories") == "超标":
            advice_parts.append(f"热量超标{-nutrition_gap['calories']:.0f}kcal，建议选择低卡菜品")
        elif status.get("calories") == "偏高":
            advice_parts.append(f"热量偏高{-nutrition_gap['calories']:.0f}kcal，注意控制食量")
        
        if status.get("fat") == "超标":
            advice_parts.append("脂肪摄入超标，建议选择清淡菜品")
        
        if not advice_parts:
            return "当前菜品搭配营养均衡，继续保持！"
        
        return "；".join(advice_parts)
    
    def has_nutritional_value(self, dish: Dish, min_score: float = 0.3) -> bool:
        nutri = dish.nutrition
        
        score = 0.0
        
        if nutri.protein >= 15:
            score += 0.3
        elif nutri.protein >= 8:
            score += 0.15
        
        if nutri.fiber >= 3:
            score += 0.2
        elif nutri.fiber >= 1.5:
            score += 0.1
        
        if nutri.calories <= 300 and nutri.protein >= 10:
            score += 0.2
        elif nutri.calories <= 500:
            score += 0.1
        
        if nutri.fat <= 20:
            score += 0.15
        elif nutri.fat > 50 and nutri.calories > 500:
            score -= 0.2
        
        vitamins_minerals = any(ing in dish.ingredients for ing in 
            ["蔬菜", "青椒", "胡萝卜", "豆腐", "鱼", "虾", "鸡蛋", "牛奶"])
        if vitamins_minerals:
            score += 0.15
        
        is_junk = nutri.calories > 600 and nutri.fat > 40 and nutri.protein < 10
        if is_junk:
            score -= 0.3
        
        return score >= min_score
    
    def filter_nutritious_dishes(
        self,
        dishes: Dict[str, Dish],
        dish_ids: List[str]
    ) -> List[str]:
        return [d_id for d_id in dish_ids if self.has_nutritional_value(dishes[d_id])]
