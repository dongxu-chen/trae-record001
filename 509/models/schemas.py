from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
from datetime import datetime


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class Allergen(str, Enum):
    PEANUT = "peanut"
    SHELLFISH = "shellfish"
    MILK = "milk"
    EGG = "egg"
    WHEAT = "wheat"
    SOY = "soy"
    FISH = "fish"
    NUTS = "nuts"
    SESAME = "sesame"
    MUSTARD = "mustard"
    CELERY = "celery"
    LUPIN = "lupin"
    MOLLUSCS = "molluscs"
    SULPHITES = "sulphites"


class CouponType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_N_GET_ONE = "buy_n_get_one"
    FREE_DELIVERY = "free_delivery"
    FIRST_ORDER = "first_order"


class SubstituteReason(str, Enum):
    SOLD_OUT = "sold_out"
    ALLERGY_CONFLICT = "allergy_conflict"
    PREFERENCE_MATCH = "preference_match"
    NUTRITION_BALANCE = "nutrition_balance"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class HealthData(BaseModel):
    height: Optional[float] = Field(None, description="身高 (cm)")
    weight: Optional[float] = Field(None, description="体重 (kg)")
    bmi: Optional[float] = Field(None, description="BMI指数")
    activity_level: ActivityLevel = Field(default=ActivityLevel.MODERATE, description="运动量等级")
    target_weight: Optional[float] = Field(None, description="目标体重 (kg)")
    health_conditions: List[str] = Field(default_factory=list, description="健康状况，如：高血压、糖尿病等")


class NutritionInfo(BaseModel):
    calories: float = Field(..., description="卡路里 (kcal)")
    protein: float = Field(..., description="蛋白质 (g)")
    fat: float = Field(..., description="脂肪 (g)")
    carbohydrates: float = Field(..., description="碳水化合物 (g)")
    fiber: float = Field(..., description="膳食纤维 (g)")


class UserPreference(BaseModel):
    taste_preferences: List[str] = Field(default_factory=list, description="口味偏好，如：辣、甜、酸等")
    cuisine_preferences: List[str] = Field(default_factory=list, description="菜系偏好，如：川菜、粤菜等")
    disliked_ingredients: List[str] = Field(default_factory=list, description="不喜欢的食材")
    diet_restrictions: List[str] = Field(default_factory=list, description="饮食限制，如：素食、低糖等")


class User(BaseModel):
    user_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    allergens: List[Allergen] = Field(default_factory=list, description="过敏源列表")
    preferences: UserPreference = Field(default_factory=UserPreference)
    order_history: List[str] = Field(default_factory=list, description="历史订单菜品ID列表")
    health_data: HealthData = Field(default_factory=HealthData, description="健康数据")


class Dish(BaseModel):
    dish_id: str
    name: str
    description: str
    price: float
    cuisine: str
    taste_tags: List[str] = Field(default_factory=list)
    ingredients: List[str] = Field(default_factory=list)
    season: Optional[Season] = None
    nutrition: NutritionInfo
    allergens: List[Allergen] = Field(default_factory=list)
    popularity_score: float = Field(default=0.0, description="热度评分 0-10")
    image_url: Optional[str] = None
    is_available: bool = Field(default=True, description="是否可售（未沽清）")
    stock_quantity: int = Field(default=100, description="库存数量")


class AllergenKnowledge(BaseModel):
    allergen: Allergen
    common_names: List[str] = Field(default_factory=list)
    related_ingredients: List[str] = Field(default_factory=list)
    cross_reactivity: List[Allergen] = Field(default_factory=list)
    severity_level: str = Field(default="medium")
    description: str = ""
    avoidance_tips: List[str] = Field(default_factory=list)


class Coupon(BaseModel):
    coupon_id: str
    name: str
    coupon_type: CouponType
    discount_value: float = Field(..., description="折扣值：百分比或固定金额")
    min_order_amount: float = Field(default=0.0, description="最低消费金额")
    max_discount: Optional[float] = None
    buy_n_quantity: Optional[int] = None
    valid_from: datetime
    valid_until: datetime
    description: str = ""
    applicable_dish_ids: List[str] = Field(default_factory=list)
    applicable_cuisines: List[str] = Field(default_factory=list)
    is_active: bool = True


class DishSubstitute(BaseModel):
    original_dish_id: str
    original_dish_name: str
    substitute_dish_id: str
    substitute_dish_name: str
    similarity_score: float
    substitute_reason: SubstituteReason
    price_difference: float
    explanation: str = ""


class CartSubstitutionResponse(BaseModel):
    original_cart: List[str]
    substitutions: List[DishSubstitute]
    final_cart: List[str]
    total_price_change: float


class CouponRecommendation(BaseModel):
    coupon: Coupon
    current_total: float
    required_amount: float
    amount_to_add: float
    suggestion_dishes: List[DishRecommendation] = Field(default_factory=list)
    savings_amount: float


class AddOnRecommendation(BaseModel):
    add_on_dish: DishRecommendation
    price: float
    reason: str
    contributes_to_coupon: bool = False
    coupon_id: Optional[str] = None


class OrderItem(BaseModel):
    dish_id: str
    quantity: int
    rating: Optional[float] = None


class Order(BaseModel):
    order_id: str
    user_id: str
    items: List[OrderItem]
    order_time: datetime
    total_amount: float
    is_group_order: bool = False
    group_members: List[str] = Field(default_factory=list)


class DishRecommendation(BaseModel):
    dish_id: str
    dish_name: str
    score: float = Field(..., description="推荐评分 0-1")
    reason: str = Field(..., description="推荐理由")
    matched_features: List[str] = Field(default_factory=list)


class TasteConflict(BaseModel):
    conflict_tastes: Tuple[str, str]
    severity: str = Field(..., description="冲突严重程度: mild, medium, severe")
    description: str


class PersonalizedNutritionTarget(BaseModel):
    calories: float
    protein: float
    fat: float
    carbohydrates: float
    fiber: float


class NutritionAdvice(BaseModel):
    advice: str
    suggestion_dish_ids: List[str] = Field(default_factory=list)
    nutrition_gap: Dict[str, float] = Field(default_factory=dict)
    nutrition_target: Optional[PersonalizedNutritionTarget] = None
    current_nutrition: Optional[Dict[str, float]] = None
    bmi_category: Optional[str] = None
    conflicts_found: List[TasteConflict] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_id: str
    current_season: Season
    budget: Optional[float] = None
    exclude_dish_ids: List[str] = Field(default_factory=list)
    top_n: int = 10


class GroupRecommendationRequest(BaseModel):
    user_ids: List[str]
    current_season: Season
    budget: Optional[float] = None
    exclude_dish_ids: List[str] = Field(default_factory=list)
    dishes_per_person: float = 1.5
    balance_types: List[str] = Field(default_factory=lambda: ["meat_vegetable", "nutrition"])


class RecommendationResponse(BaseModel):
    recommendations: List[DishRecommendation]
    nutrition_advice: NutritionAdvice
    filtered_allergens: List[Allergen]
    season_recommendations: List[str]
