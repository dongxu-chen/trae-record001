from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
from enum import Enum
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.models import (
    Song, User, UserBehavior, RecommendationResponse,
    RecommendationItem, Genre, ActionType
)
from data.data_generator import DataGenerator
from recommenders import (
    CollaborativeFilteringRecommender,
    ContentFilteringRecommender,
    HybridRecommender,
    MultimodalSimilarity,
    PlaylistGenerator,
    RecommendationCache,
    GeneratedPlaylist
)
from config import settings

app = FastAPI(
    title="Music Recommendation System API",
    description="混合音乐推荐系统 - 支持协同过滤、内容过滤、多模态特征、实时反馈、歌单生成",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActionType(str, Enum):
    LIKE = "like"
    PLAY_COMPLETE = "play_complete"
    PLAY_PARTIAL = "play_partial"
    SKIP = "skip"
    DISLIKE = "dislike"


class AppState:
    def __init__(self):
        self.songs: List[Song] = []
        self.users: List[User] = []
        self.ratings_df: pd.DataFrame = None
        self.cf_recommender: CollaborativeFilteringRecommender = None
        self.content_recommender: ContentFilteringRecommender = None
        self.multimodal: MultimodalSimilarity = None
        self.playlist_generator: PlaylistGenerator = None
        self.hybrid_recommender: HybridRecommender = None
        self.cache: RecommendationCache = None
        self.initialized = False


state = AppState()


@app.on_event("startup")
async def startup_event():
    await initialize_system()


async def initialize_system():
    print("=" * 60)
    print("Initializing music recommendation system v2.0...")
    print("=" * 60)
    
    print("\n1. Generating sample data...")
    data_gen = DataGenerator()
    state.songs = data_gen.generate_songs(num_songs=100)
    state.users = data_gen.generate_users(num_users=50)
    data_gen.generate_behaviors(min_behaviors_per_user=10, max_behaviors_per_user=30)
    state.ratings_df = data_gen.get_ratings_dataframe()
    
    print(f"   Generated {len(state.songs)} songs, {len(state.users)} users")
    print(f"   Total ratings: {len(state.ratings_df)}")
    
    print("\n2. Training collaborative filtering model...")
    state.cf_recommender = CollaborativeFilteringRecommender()
    cf_metrics = state.cf_recommender.train(state.ratings_df, method="svd")
    print(f"   CF Model - RMSE: {cf_metrics['rmse']:.4f}, MAE: {cf_metrics['mae']:.4f}")
    
    print("\n3. Building content-based similarity matrix...")
    state.content_recommender = ContentFilteringRecommender()
    songs_df = data_gen.get_songs_dataframe()
    state.content_recommender.build_feature_matrix(songs_df)
    state.content_recommender.compute_similarity_matrix()
    print("   Content model built successfully")
    
    print("\n4. Building multimodal features (image + text)...")
    state.multimodal = MultimodalSimilarity(
        image_weight=0.3,
        text_weight=0.3,
        content_weight=0.4
    )
    state.multimodal.build_multimodal_features(songs_df)
    state.multimodal.combine_with_content_similarity(state.content_recommender.similarity_matrix)
    print("   Multimodal features built successfully")
    
    print("\n5. Initializing playlist generator...")
    state.playlist_generator = PlaylistGenerator()
    print("   Playlist generator ready")
    
    print("\n6. Initializing hybrid recommender...")
    state.cache = RecommendationCache()
    state.hybrid_recommender = HybridRecommender(
        cf_recommender=state.cf_recommender,
        content_recommender=state.content_recommender,
        multimodal=state.multimodal,
        cache=state.cache,
        multimodal_weight=0.3
    )
    state.hybrid_recommender.set_songs(state.songs)
    print("   Hybrid recommender ready")
    
    state.initialized = True
    print("\n" + "=" * 60)
    print("System initialized successfully!")
    print("=" * 60)


@app.get("/")
async def root():
    return {
        "message": "Music Recommendation System API v2.0",
        "version": "2.0.0",
        "status": "initialized" if state.initialized else "initializing",
        "features": [
            "Hybrid Recommendation (CF + Content)",
            "Multimodal Features (Image + Text)",
            "Real-time Feedback Update",
            "Smart Playlist Generation",
            "Dynamic Weight Adjustment",
            "Epsilon Decay Exploration"
        ]
    }


@app.get("/api/recommendations/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    top_n: int = Query(default=10, ge=1, le=50),
    use_bandit: bool = Query(default=True),
    use_cache: bool = Query(default=True),
    use_multimodal: bool = Query(default=True)
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    recommendations = state.hybrid_recommender.hybrid_recommend(
        user_id=user_id,
        ratings_df=state.ratings_df,
        top_n=top_n,
        use_bandit=use_bandit,
        use_cache=use_cache,
        use_multimodal=use_multimodal
    )
    
    return RecommendationResponse(
        user_id=user_id,
        recommendations=recommendations,
        timestamp=datetime.now()
    )


@app.get("/api/recommendations/similar/{song_id}", response_model=List[RecommendationItem])
async def get_similar_songs(
    song_id: str,
    top_n: int = Query(default=10, ge=1, le=50),
    use_multimodal: bool = Query(default=True)
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(s.song_id == song_id for s in state.songs):
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    
    return state.hybrid_recommender.recommend_similar_songs(
        song_id, top_n=top_n, use_multimodal=use_multimodal
    )


@app.get("/api/recommendations/explore/{user_id}", response_model=List[RecommendationItem])
async def get_explore_recommendations(
    user_id: str,
    top_n: int = Query(default=5, ge=1, le=20)
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return state.hybrid_recommender.get_explore_recommendations(user_id, top_n=top_n)


@app.post("/api/feedback/{user_id}/{song_id}")
async def post_feedback(
    user_id: str,
    song_id: str,
    action: ActionType
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    if not any(s.song_id == song_id for s in state.songs):
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    
    state.hybrid_recommender.record_user_action(user_id, song_id, action.value)
    
    action_weights = {
        "like": 2.0,
        "play_complete": 1.0,
        "play_partial": 0.3,
        "skip": -1.0,
        "dislike": -2.0
    }
    
    return {
        "message": "Feedback recorded successfully",
        "user_id": user_id,
        "song_id": song_id,
        "action": action.value,
        "weight": action_weights[action.value],
        "cache_invalidated": True
    }


@app.get("/api/users/{user_id}/skip-stats")
async def get_user_skip_stats(user_id: str):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return state.hybrid_recommender.get_user_skip_stats(user_id)


@app.get("/api/playlists/themes")
async def get_playlist_themes():
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    return {
        "themes": state.playlist_generator.get_all_themes()
    }


@app.post("/api/playlists/generate/{user_id}", response_model=GeneratedPlaylist)
async def generate_playlist(
    user_id: str,
    theme_id: Optional[str] = Query(None, description="歌单主题ID，不传则自动检测"),
    playlist_size: int = Query(default=20, ge=5, le=100)
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    recommendations = state.hybrid_recommender.hybrid_recommend(
        user_id=user_id,
        ratings_df=state.ratings_df,
        top_n=playlist_size * 3,
        use_bandit=False,
        use_cache=False,
        use_multimodal=True
    )
    
    rec_dicts = [rec.model_dump() for rec in recommendations]
    
    selected_theme = None
    if theme_id:
        for theme in state.playlist_generator.themes:
            if theme.theme_id == theme_id:
                selected_theme = theme
                break
        if not selected_theme:
            raise HTTPException(status_code=404, detail=f"Theme {theme_id} not found")
    
    playlist = state.playlist_generator.generate_from_recommendations(
        recommendations=rec_dicts,
        theme=selected_theme,
        playlist_size=playlist_size
    )
    
    return playlist


@app.post("/api/playlists/smart-mix/{user_id}", response_model=GeneratedPlaylist)
async def generate_smart_mix(
    user_id: str,
    playlist_size: int = Query(default=30, ge=10, le=100)
):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user_recs = state.hybrid_recommender.hybrid_recommend(
        user_id=user_id,
        ratings_df=state.ratings_df,
        top_n=50,
        use_bandit=False,
        use_cache=False
    )
    user_rec_dicts = [rec.model_dump() for rec in user_recs]
    
    top_song_id = user_rec_dicts[0]["song_id"] if user_rec_dicts else state.songs[0].song_id
    similar_songs = state.hybrid_recommender.recommend_similar_songs(top_song_id, top_n=20)
    similar_dicts = [rec.model_dump() for rec in similar_songs]
    
    explore_songs = state.hybrid_recommender.get_explore_recommendations(user_id, top_n=15)
    explore_dicts = [rec.model_dump() for rec in explore_songs]
    
    playlist = state.playlist_generator.generate_smart_mix(
        user_recommendations=user_rec_dicts,
        similar_songs=similar_dicts,
        explore_songs=explore_dicts,
        playlist_size=playlist_size
    )
    
    return playlist


@app.get("/api/songs", response_model=List[Song])
async def get_songs(
    genre: Optional[Genre] = None,
    artist: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    result = state.songs
    
    if genre:
        result = [s for s in result if s.genre == genre]
    
    if artist:
        result = [s for s in result if artist.lower() in s.artist.lower()]
    
    return result[:limit]


@app.get("/api/songs/{song_id}", response_model=Song)
async def get_song(song_id: str):
    for song in state.songs:
        if song.song_id == song_id:
            return song
    raise HTTPException(status_code=404, detail=f"Song {song_id} not found")


@app.get("/api/users", response_model=List[User])
async def get_users(limit: int = Query(default=20, ge=1, le=100)):
    return state.users[:limit]


@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    for user in state.users:
        if user.user_id == user_id:
            return user
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@app.get("/api/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    profile = state.hybrid_recommender.get_user_profile(user_id)
    return profile


@app.get("/api/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    if not any(u.user_id == user_id for u in state.users):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    user_ratings = state.ratings_df[state.ratings_df["user_id"] == user_id]
    liked_songs = user_ratings[user_ratings["rating"] >= 3.5]["song_id"].tolist()
    
    user_prefs = state.hybrid_recommender._analyze_user_preferences(liked_songs)
    
    return {
        "user_id": user_id,
        "top_genres": [{"genre": g, "count": c} for g, c in user_prefs["genres"][:5]],
        "top_artists": [{"artist": a, "count": c} for a, c in user_prefs["artists"][:5]],
        "top_decades": [{"decade": d, "count": c} for d, c in user_prefs["decades"][:3]],
        "total_liked_songs": len(liked_songs)
    }


@app.get("/api/stats")
async def get_stats():
    if not state.initialized:
        raise HTTPException(status_code=503, detail="System not initialized yet")
    
    return {
        "version": "2.0.0",
        "total_songs": len(state.songs),
        "total_users": len(state.users),
        "total_ratings": len(state.ratings_df),
        "genres": list(Genre),
        "weights": {
            "base_cf_weight": settings.CF_WEIGHT,
            "base_content_weight": settings.CONTENT_WEIGHT,
            "multimodal_weight": 0.3
        },
        "dynamic_weight_description": "新用户: 20% CF + 80% Content, 活跃用户: 80% CF + 20% Content",
        "epsilon_decay_description": "探索率随用户活跃度指数衰减，最低2%",
        "features": {
            "multimodal": True,
            "realtime_feedback": True,
            "playlist_generation": True,
            "themes_count": len(state.playlist_generator.themes) if state.playlist_generator else 0
        }
    }


@app.post("/api/refresh")
async def refresh_models():
    await initialize_system()
    return {"message": "All models refreshed successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
