from fastapi import FastAPI, HTTPException
from typing import List, Optional
from models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    GroupRecommendationRequest,
    DishRecommendation,
    Dish,
    User,
    Season
)
from data import create_sample_users, create_sample_dishes, create_sample_orders
from engine import RecommendationEngine

app = FastAPI(
    title="餐厅菜品推荐系统 API",
    description="基于协同过滤、关联规则和知识图谱的智能菜品推荐系统",
    version="1.0.0"
)

users = create_sample_users()
dishes = create_sample_dishes()
orders = create_sample_orders(users, dishes)
recommendation_engine = RecommendationEngine(users, dishes, orders)


@app.get("/")
async def root():
    return {
        "message": "餐厅菜品推荐系统 API",
        "version": "1.0.0",
        "endpoints": {
            "/recommend": "个性化菜品推荐",
            "/recommend/group": "多人点餐组合推荐",
            "/recommend/cart": "购物车关联推荐",
            "/dishes/similar/{dish_id}": "相似菜品推荐",
            "/users": "获取所有用户",
            "/users/{user_id}": "获取用户信息",
            "/dishes": "获取所有菜品",
            "/dishes/{dish_id}": "获取菜品详情"
        }
    }


@app.post("/recommend", response_model=RecommendationResponse)
async def get_personalized_recommendations(request: RecommendationRequest):
    if request.user_id not in users:
        raise HTTPException(status_code=404, detail=f"用户 {request.user_id} 不存在")
    
    recommendations, filtered_allergens, seasonal_recs = recommendation_engine.get_personalized_recommendations(
        user_id=request.user_id,
        current_season=request.current_season,
        exclude_dish_ids=request.exclude_dish_ids,
        top_n=request.top_n,
        budget=request.budget
    )
    
    nutrition_advice = recommendation_engine.get_nutrition_advice(
        [r.dish_id for r in recommendations[:5]],
        ["nutrition"]
    )
    
    return RecommendationResponse(
        recommendations=recommendations,
        nutrition_advice=nutrition_advice,
        filtered_allergens=filtered_allergens,
        season_recommendations=seasonal_recs
    )


@app.post("/recommend/group", response_model=RecommendationResponse)
async def get_group_recommendations(request: GroupRecommendationRequest):
    for user_id in request.user_ids:
        if user_id not in users:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    
    recommendations, nutrition_advice, filtered_allergens, seasonal_recs = recommendation_engine.get_group_recommendations(
        user_ids=request.user_ids,
        current_season=request.current_season,
        exclude_dish_ids=request.exclude_dish_ids,
        dishes_per_person=request.dishes_per_person,
        balance_types=request.balance_types,
        budget=request.budget
    )
    
    return RecommendationResponse(
        recommendations=recommendations,
        nutrition_advice=nutrition_advice,
        filtered_allergens=filtered_allergens,
        season_recommendations=seasonal_recs
    )


@app.get("/recommend/cart")
async def get_cart_recommendations(
    dish_ids: str,
    user_id: Optional[str] = None,
    top_n: int = 5
):
    cart_dish_ids = [d.strip() for d in dish_ids.split(",") if d.strip()]
    
    invalid_dishes = [d for d in cart_dish_ids if d not in dishes]
    if invalid_dishes:
        raise HTTPException(status_code=404, detail=f"菜品不存在: {invalid_dishes}")
    
    if user_id and user_id not in users:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    
    recommendations = recommendation_engine.get_associated_dishes_for_cart(
        cart_dish_ids=cart_dish_ids,
        user_id=user_id,
        top_n=top_n
    )
    
    return {"recommendations": recommendations}


@app.get("/dishes/similar/{dish_id}")
async def get_similar_dishes(
    dish_id: str,
    user_id: Optional[str] = None,
    top_n: int = 5
):
    if dish_id not in dishes:
        raise HTTPException(status_code=404, detail=f"菜品 {dish_id} 不存在")
    
    if user_id and user_id not in users:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    
    similar_dishes = recommendation_engine.get_similar_dishes(
        dish_id=dish_id,
        user_id=user_id,
        top_n=top_n
    )
    
    return {"similar_dishes": similar_dishes}


@app.get("/users")
async def get_all_users():
    return {"users": list(users.values())}


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    if user_id not in users:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return users[user_id]


@app.get("/dishes")
async def get_all_dishes(
    cuisine: Optional[str] = None,
    season: Optional[Season] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    result = list(dishes.values())
    
    if cuisine:
        result = [d for d in result if d.cuisine == cuisine]
    
    if season:
        result = [d for d in result if d.season == season or d.season is None]
    
    if min_price is not None:
        result = [d for d in result if d.price >= min_price]
    
    if max_price is not None:
        result = [d for d in result if d.price <= max_price]
    
    return {"dishes": result}


@app.get("/dishes/{dish_id}")
async def get_dish(dish_id: str):
    if dish_id not in dishes:
        raise HTTPException(status_code=404, detail=f"菜品 {dish_id} 不存在")
    return dishes[dish_id]


@app.get("/nutrition/analyze")
async def analyze_nutrition(dish_ids: str):
    dish_id_list = [d.strip() for d in dish_ids.split(",") if d.strip()]
    
    invalid_dishes = [d for d in dish_id_list if d not in dishes]
    if invalid_dishes:
        raise HTTPException(status_code=404, detail=f"菜品不存在: {invalid_dishes}")
    
    nutrition_advice = recommendation_engine.get_nutrition_advice(
        dish_id_list,
        ["nutrition"]
    )
    
    return {
        "selected_dishes": [{"id": d, "name": dishes[d].name} for d in dish_id_list],
        "nutrition_advice": nutrition_advice
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
