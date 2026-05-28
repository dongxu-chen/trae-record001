from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os
from typing import Optional, List

from data_generator import generate_all_data
from recommender import CollaborativeFilteringRecommender
from boxoffice_predictor import BoxOfficePredictor
from preference_analyzer import PreferenceAnalyzer

app = FastAPI(
    title="电影推荐与票房预测系统",
    description="结合用户画像和电影特征，提供个性化推荐和票房预测。支持冷启动人口统计学推荐、层次聚类、宣发费用智能填充、序列推荐、多样性控制、观影时间预测。",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

movies_df = None
users_df = None
ratings_df = None
boxoffice_df = None

recommender = None
boxoffice_predictor = None
preference_analyzer = None


class MovieFeatures(BaseModel):
    movie_id: str
    title: str
    genres: str
    actors: str
    director: str
    release_year: int
    budget: int
    runtime: int
    is_sequel: int
    production_company: str


class BoxOfficeContext(BaseModel):
    release_month: Optional[int] = 7
    release_weekday: Optional[int] = 4
    holiday_season: Optional[int] = 1
    marketing_spend: Optional[float] = None
    num_screens: Optional[int] = 4000


class ColdStartUser(BaseModel):
    user_id: str
    age_group: str
    gender: str
    occupation: str
    city: str
    watch_frequency: str
    genre_preferences: Optional[dict] = None


def initialize_data():
    global movies_df, users_df, ratings_df, boxoffice_df
    global recommender, boxoffice_predictor, preference_analyzer

    print("正在初始化系统...")

    os.makedirs('data', exist_ok=True)

    if not os.path.exists('data/movies.csv'):
        print("未找到数据文件，正在生成模拟数据...")
        movies_df, users_df, ratings_df, boxoffice_df = generate_all_data()
    else:
        print("加载现有数据...")
        movies_df = pd.read_csv('data/movies.csv')
        users_df = pd.read_csv('data/users.csv')
        ratings_df = pd.read_csv('data/ratings.csv')
        boxoffice_df = pd.read_csv('data/boxoffice.csv')

    print("训练协同过滤推荐模型（含层次聚类+人口统计学冷启动）...")
    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    print("训练票房预测模型（含宣发费用智能填充）...")
    boxoffice_predictor = BoxOfficePredictor()
    if not os.path.exists('models/boxoffice_model.txt'):
        boxoffice_predictor.train(movies_df, boxoffice_df)
    else:
        boxoffice_predictor.load_model()

    preference_analyzer = PreferenceAnalyzer()

    print("系统初始化完成！")


@app.on_event("startup")
async def startup_event():
    initialize_data()


@app.get("/")
async def root():
    return {
        "message": "电影推荐与票房预测系统 v2.0",
        "features": [
            "协同过滤推荐（混合/基于用户/基于物品）",
            "冷启动用户：人口统计学推荐 + 快速探索",
            "层次聚类：动态决定聚类数",
            "票房预测：宣发费用历史均值+热度预估填充"
        ],
        "endpoints": {
            "recommend": "/api/recommend/{user_id}",
            "cold_start_recommend": "/api/recommend/cold-start",
            "boxoffice_predict": "/api/boxoffice/predict/{movie_id}",
            "marketing_estimate": "/api/boxoffice/marketing-estimate/{movie_id}",
            "user_preferences": "/api/user/{user_id}/preferences",
            "similar_users": "/api/user/{user_id}/similar",
            "similar_movies": "/api/movie/{movie_id}/similar",
            "cluster_info": "/api/cluster/info",
            "cluster_user_info": "/api/cluster/{user_id}",
            "movies": "/api/movies",
            "users": "/api/users"
        }
    }


@app.get("/api/movies")
async def get_movies(limit: int = 50):
    if movies_df is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    result = movies_df.head(limit).to_dict('records')
    return {"count": len(result), "movies": result}


@app.get("/api/users")
async def get_users(limit: int = 50):
    if users_df is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    result = users_df.head(limit).drop(columns=[col for col in users_df.columns if col.startswith('pref_')]).to_dict('records')
    return {"count": len(result), "users": result}


@app.get("/api/recommend/{user_id}")
async def get_recommendations(user_id: str, top_n: int = 10, method: str = "hybrid", include_boxoffice: bool = True, explore_ratio: Optional[float] = None):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    is_cold_start = recommender._is_cold_start(user_id)

    if user_id not in users_df['user_id'].values and not is_cold_start:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    recommendations = recommender.recommend(user_id, top_n=top_n, method=method, explore_ratio=explore_ratio)

    if include_boxoffice and boxoffice_predictor is not None:
        for rec in recommendations:
            movie_row = movies_df[movies_df['movie_id'] == rec['movie_id']]
            if len(movie_row) > 0:
                movie_features = movie_row.iloc[0].to_dict()
                boxoffice_pred = boxoffice_predictor.predict_with_interval(movie_features)
                rec['boxoffice_prediction'] = boxoffice_pred

    return {
        "user_id": user_id,
        "method": method,
        "is_cold_start": is_cold_start,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations
    }


@app.post("/api/recommend/cold-start")
async def cold_start_recommend(user: ColdStartUser, top_n: int = 10, explore_ratio: Optional[float] = None):
    if recommender is None or users_df is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    new_user_data = {
        'user_id': user.user_id,
        'age_group': user.age_group,
        'gender': user.gender,
        'occupation': user.occupation,
        'city': user.city,
        'watch_frequency': user.watch_frequency
    }

    genre_prefs = user.genre_preferences or {}
    for genre in ['动作', '喜剧', '剧情', '科幻', '恐怖', '爱情', '动画', '悬疑', '冒险', '战争']:
        new_user_data[f'pref_{genre}'] = genre_prefs.get(genre, 0.5)

    new_user_row = pd.Series(new_user_data)

    if user.user_id not in users_df['user_id'].values:
        temp_users = pd.concat([users_df, pd.DataFrame([new_user_data])], ignore_index=True)
    else:
        temp_users = users_df

    original_users_df = recommender.users_df
    recommender.users_df = temp_users

    recommendations = recommender._recommend_cold_start_demographic(user.user_id, top_n, explore_ratio)

    recommender.users_df = original_users_df

    if boxoffice_predictor is not None:
        for rec in recommendations:
            movie_row = movies_df[movies_df['movie_id'] == rec['movie_id']]
            if len(movie_row) > 0:
                movie_features = movie_row.iloc[0].to_dict()
                boxoffice_pred = boxoffice_predictor.predict_with_interval(movie_features)
                rec['boxoffice_prediction'] = boxoffice_pred

    return {
        "user_id": user.user_id,
        "is_cold_start": True,
        "recommendation_method": "demographic_exploration",
        "recommendation_count": len(recommendations),
        "recommendations": recommendations
    }


@app.get("/api/boxoffice/predict/{movie_id}")
async def predict_boxoffice(movie_id: str, confidence: float = 0.9):
    if boxoffice_predictor is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    movie_row = movies_df[movies_df['movie_id'] == movie_id]
    if len(movie_row) == 0:
        raise HTTPException(status_code=404, detail=f"电影 {movie_id} 不存在")

    movie_features = movie_row.iloc[0].to_dict()
    prediction = boxoffice_predictor.predict_with_interval(movie_features, confidence=confidence)

    boxoffice_row = boxoffice_df[boxoffice_df['movie_id'] == movie_id]
    actual_opening = None
    if len(boxoffice_row) > 0:
        actual_opening = int(boxoffice_row.iloc[0]['opening_weekend_revenue'])

    return {
        "movie_id": movie_id,
        "title": movie_features['title'],
        "prediction": prediction,
        "actual_opening_weekend": actual_opening
    }


@app.get("/api/boxoffice/marketing-estimate/{movie_id}")
async def estimate_marketing(movie_id: str):
    if boxoffice_predictor is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    movie_row = movies_df[movies_df['movie_id'] == movie_id]
    if len(movie_row) == 0:
        raise HTTPException(status_code=404, detail=f"电影 {movie_id} 不存在")

    movie_features = movie_row.iloc[0].to_dict()
    estimate = boxoffice_predictor.get_marketing_estimate(movie_features)

    return {
        "movie_id": movie_id,
        "title": movie_features['title'],
        "marketing_estimate": estimate
    }


@app.post("/api/boxoffice/predict/custom")
async def predict_custom_boxoffice(movie_features: MovieFeatures, context: BoxOfficeContext, confidence: float = 0.9):
    if boxoffice_predictor is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    movie_dict = movie_features.dict()

    if context.marketing_spend is None:
        estimated = boxoffice_predictor._compute_marketing_from_history(movie_dict)
        context.marketing_spend = estimated

    boxoffice_context = pd.DataFrame([{
        'movie_id': movie_dict['movie_id'],
        'release_month': context.release_month,
        'release_weekday': context.release_weekday,
        'holiday_season': context.holiday_season,
        'marketing_spend': context.marketing_spend,
        'num_screens': context.num_screens
    }])

    prediction = boxoffice_predictor.predict_with_interval(movie_dict, boxoffice_context, confidence=confidence)

    return {
        "movie_id": movie_dict['movie_id'],
        "title": movie_dict['title'],
        "prediction": prediction
    }


@app.get("/api/user/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    if preference_analyzer is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    analysis = preference_analyzer.analyze_user_preferences(user_id, ratings_df, movies_df, users_df)

    return analysis


@app.get("/api/user/{user_id}/similar")
async def get_similar_users(user_id: str, top_n: int = 5):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    is_cold_start = recommender._is_cold_start(user_id)

    if user_id not in users_df['user_id'].values and not is_cold_start:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    similar_users = recommender.get_similar_users(user_id, top_n=top_n)

    for user in similar_users:
        user_row = users_df[users_df['user_id'] == user['user_id']]
        if len(user_row) > 0:
            user['age_group'] = user_row.iloc[0]['age_group']
            user['occupation'] = user_row.iloc[0]['occupation']

    return {
        "user_id": user_id,
        "is_cold_start": is_cold_start,
        "similar_users": similar_users
    }


@app.get("/api/movie/{movie_id}/similar")
async def get_similar_movies(movie_id: str, top_n: int = 5):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if movie_id not in movies_df['movie_id'].values:
        raise HTTPException(status_code=404, detail=f"电影 {movie_id} 不存在")

    similar_movies = recommender.get_similar_movies(movie_id, top_n=top_n)

    return {
        "movie_id": movie_id,
        "similar_movies": similar_movies
    }


@app.get("/api/cluster/info")
async def get_cluster_info():
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    info = recommender.get_cluster_info()

    return {
        "cluster_method": "hierarchical_ward",
        "cluster_info": info
    }


@app.get("/api/cluster/{user_id}")
async def get_user_cluster(user_id: str):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    info = recommender.get_cluster_info(user_id)
    is_cold_start = recommender._is_cold_start(user_id)

    return {
        "user_id": user_id,
        "is_cold_start": is_cold_start,
        "cluster_info": info
    }


@app.get("/api/recommend/{user_id}/sequence")
async def get_sequence_recommendations(user_id: str, top_n: int = 10, sequence_weight: float = 0.3):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    recommendations = recommender.recommend_sequence(user_id, top_n=top_n, sequence_weight=sequence_weight)

    return {
        "user_id": user_id,
        "method": "sequence_aware",
        "sequence_weight": sequence_weight,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations
    }


@app.get("/api/recommend/{user_id}/diverse")
async def get_diverse_recommendations(user_id: str, top_n: int = 10, diversity_weight: float = 0.25, method: str = "greedy"):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    if method not in ["greedy", "mmr"]:
        raise HTTPException(status_code=400, detail="method 必须是 'greedy' 或 'mmr'")

    recommendations = recommender.recommend_with_diversity(
        user_id, top_n=top_n, diversity_weight=diversity_weight, diversity_method=method
    )

    return {
        "user_id": user_id,
        "diversity_method": method,
        "diversity_weight": diversity_weight,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations
    }


@app.get("/api/recommend/{user_id}/runtime")
async def get_runtime_recommendations(user_id: str, available_minutes: int, top_n: int = 10, tolerance: int = 15):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    if available_minutes < 30:
        raise HTTPException(status_code=400, detail="available_minutes 必须至少为30分钟")

    result = recommender.recommend_by_runtime(
        user_id, available_minutes=available_minutes, top_n=top_n, tolerance=tolerance
    )

    return result


@app.get("/api/user/{user_id}/sequence-analysis")
async def get_user_sequence_analysis(user_id: str):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    analysis = recommender.get_user_sequence_analysis(user_id)

    return analysis


@app.get("/api/user/{user_id}/watch-time")
async def get_user_watch_time_analysis(user_id: str):
    if recommender is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    if user_id not in users_df['user_id'].values:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    analysis = recommender.get_user_watch_time_analysis(user_id)

    return analysis


@app.get("/api/boxoffice/feature-importance")
async def get_feature_importance(top_n: int = 15):
    if boxoffice_predictor is None:
        raise HTTPException(status_code=500, detail="系统未初始化")

    importance = boxoffice_predictor.get_feature_importance(top_n=top_n)

    return {"feature_importance": importance}


@app.post("/api/data/regenerate")
async def regenerate_data():
    global movies_df, users_df, ratings_df, boxoffice_df
    global recommender, boxoffice_predictor

    movies_df, users_df, ratings_df, boxoffice_df = generate_all_data()

    recommender = CollaborativeFilteringRecommender(n_neighbors=20, n_clusters=None, exploration_ratio=0.2)
    recommender.fit(ratings_df, users_df, movies_df)

    boxoffice_predictor = BoxOfficePredictor()
    boxoffice_predictor.train(movies_df, boxoffice_df)

    return {"message": "数据重新生成并训练完成"}


@app.get("/api/features")
async def get_features_info():
    return {
        "available_features": {
            "recommendation": [
                "协同过滤推荐（用户/物品/混合）",
                "冷启动人口统计学推荐",
                "序列感知推荐（捕捉偏好演变）",
                "多样性控制推荐（Greedy/MMR）",
                "按时长推荐（匹配空闲时间）"
            ],
            "user_analysis": [
                "用户观影序列分析",
                "观影时间模式分析",
                "用户偏好聚类（层次聚类）",
                "相似用户查找"
            ],
            "boxoffice": [
                "LightGBM票房预测",
                "宣发费用智能填充（历史均值+热度）",
                "置信区间预测",
                "特征重要性分析"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
