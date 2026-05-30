from fastapi import FastAPI, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime
from models import (
    User, Book, Rating, SocialConnection,
    RecommendationRequest, RecommendationResult,
    BookSeries, ReadingProgress, ReadingPrediction,
    BookReviewSummary
)
from data_store import DataStore
from hybrid_recommender import HybridRecommender
from sample_data import create_sample_data

app = FastAPI(
    title="图书推荐系统 API",
    description="基于协同过滤、矩阵分解和社交图的个性化图书推荐系统",
    version="1.0.0"
)

data_store = DataStore()
recommender = HybridRecommender(data_store)


@app.on_event("startup")
async def startup_event():
    print("系统启动中...")
    print("加载示例数据...")
    create_sample_data(data_store)
    print("模型训练中...")
    recommender.train()
    print("系统启动完成！")


@app.post("/users/", response_model=User, tags=["用户管理"])
def create_user(user: User):
    data_store.add_user(user)
    return user


@app.get("/users/{user_id}", response_model=User, tags=["用户管理"])
def get_user(user_id: int):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@app.post("/books/", response_model=Book, tags=["书籍管理"])
def create_book(book: Book):
    data_store.add_book(book)
    return book


@app.get("/books/{book_id}", response_model=Book, tags=["书籍管理"])
def get_book(book_id: int):
    book = data_store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    return book


@app.get("/books/", response_model=List[Book], tags=["书籍管理"])
def list_books(skip: int = 0, limit: int = 100):
    books = list(data_store.books.values())[skip:skip + limit]
    return books


@app.post("/ratings/", response_model=Rating, tags=["评分管理"])
def create_rating(rating: Rating):
    if rating.rating < 0 or rating.rating > 5:
        raise HTTPException(status_code=400, detail="评分必须在0-5之间")
    data_store.add_rating(rating)
    recommender.train()
    return rating


@app.get("/users/{user_id}/ratings", tags=["评分管理"])
def get_user_ratings(user_id: int):
    ratings = data_store.get_user_ratings(user_id)
    return {"user_id": user_id, "ratings": ratings}


@app.post("/social/", response_model=SocialConnection, tags=["社交关系"])
def create_social_connection(conn: SocialConnection):
    if conn.user_id == conn.friend_id:
        raise HTTPException(status_code=400, detail="不能添加自己为好友")
    data_store.add_social_connection(conn)
    recommender.social_recommender.add_connection(conn.user_id, conn.friend_id)
    return conn


@app.get("/users/{user_id}/friends", tags=["社交关系"])
def get_user_friends(user_id: int):
    friends = data_store.get_user_friends(user_id)
    return {"user_id": user_id, "friends": friends}


@app.post("/recommendations/", response_model=List[RecommendationResult], tags=["推荐系统"])
def get_recommendations(request: RecommendationRequest):
    user = data_store.get_user(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    recs = recommender.recommend(
        user_id=request.user_id,
        top_n=request.top_n,
        diversity_weight=request.diversity_weight,
        exploration_rate=request.exploration_rate
    )

    results = []
    for book_id, score, reason in recs:
        book = data_store.get_book(book_id)
        if book:
            results.append(RecommendationResult(
                book_id=book_id,
                title=book.title,
                score=round(score, 3),
                reason=reason,
                genres=book.genres
            ))

    return results


@app.get("/recommendations/{user_id}/explain/{book_id}", tags=["推荐系统"])
def explain_recommendation(user_id: int, book_id: int):
    user = data_store.get_user(user_id)
    book = data_store.get_book(book_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")

    explanation = recommender.explain_recommendation(user_id, book_id)
    return explanation


@app.get("/recommendations/{user_id}/stats", tags=["推荐系统"])
def get_recommendation_stats(user_id: int):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    stats = recommender.get_recommendation_stats(user_id)
    return stats


@app.get("/popular/", response_model=List[RecommendationResult], tags=["推荐系统"])
def get_popular_books(top_n: int = 10):
    popular_ids = data_store.get_popular_books(top_n)
    
    results = []
    for book_id in popular_ids:
        book = data_store.get_book(book_id)
        if book:
            results.append(RecommendationResult(
                book_id=book_id,
                title=book.title,
                score=round(book.avg_rating, 3),
                reason="热门推荐",
                genres=book.genres
            ))
    
    return results


@app.post("/train", tags=["系统管理"])
def train_model():
    recommender.train()
    return {"status": "success", "message": "模型训练完成"}


@app.get("/stats", tags=["系统管理"])
def get_system_stats():
    return {
        "num_users": len(data_store.users),
        "num_books": len(data_store.books),
        "num_ratings": len(data_store.ratings),
        "num_series": len(data_store.book_series),
        "model_trained": recommender.matrix_factorization.is_trained
    }


@app.post("/series/", response_model=BookSeries, tags=["系列丛书"])
def create_series(series: BookSeries):
    data_store.add_book_series(series)
    return series


@app.get("/series/", response_model=List[BookSeries], tags=["系列丛书"])
def list_series():
    return data_store.get_all_series()


@app.get("/series/{series_id}", response_model=BookSeries, tags=["系列丛书"])
def get_series(series_id: int):
    series = data_store.get_book_series(series_id)
    if not series:
        raise HTTPException(status_code=404, detail="系列不存在")
    return series


@app.get("/series/{series_id}/books", tags=["系列丛书"])
def get_series_books(series_id: int):
    books = data_store.get_series_books(series_id)
    if not books:
        raise HTTPException(status_code=404, detail="系列不存在或无书籍")
    return {
        "series_id": series_id,
        "series_name": data_store.get_book_series(series_id).series_name if data_store.get_book_series(series_id) else "",
        "books": books
    }


@app.get("/books/{book_id}/series", tags=["系列丛书"])
def get_book_series(book_id: int):
    book = data_store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    series = data_store.get_book_series_by_book(book_id)
    if not series:
        return {"has_series": False, "series": None}
    series_books = data_store.get_series_books(series.series_id)
    return {
        "has_series": True,
        "series": series,
        "series_books": series_books,
        "current_order": book.series_order
    }


@app.get("/recommendations/{user_id}/series", tags=["系列丛书"])
def get_series_recommendations(user_id: int, top_n: int = 5):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    recs = recommender.series_recommender.recommend_next_in_series(user_id, top_n)
    results = []
    for book_id, score, reason in recs:
        book = data_store.get_book(book_id)
        if book:
            results.append(RecommendationResult(
                book_id=book_id,
                title=book.title,
                score=round(score, 3),
                reason=reason,
                genres=book.genres
            ))
    return results


@app.post("/reading/progress", response_model=ReadingProgress, tags=["阅读进度"])
def update_reading_progress(
    user_id: int,
    book_id: int,
    current_page: int,
    total_pages: Optional[int] = None
):
    user = data_store.get_user(user_id)
    book = data_store.get_book(book_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    
    progress = recommender.reading_predictor.update_progress(
        user_id, book_id, current_page, total_pages
    )
    return progress


@app.get("/reading/{user_id}/progress", tags=["阅读进度"])
def get_user_reading_progress(user_id: int):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    progress_list = data_store.get_user_reading_progress(user_id)
    return {
        "user_id": user_id,
        "reading_count": len(progress_list),
        "progress_list": progress_list
    }


@app.get("/reading/{user_id}/predict/{book_id}", response_model=ReadingPrediction, tags=["阅读进度"])
def predict_finish_time(user_id: int, book_id: int):
    user = data_store.get_user(user_id)
    book = data_store.get_book(book_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    
    prediction = recommender.reading_predictor.predict_finish_time(user_id, book_id)
    if not prediction:
        raise HTTPException(status_code=400, detail="无法预测阅读时间")
    return prediction


@app.get("/reading/{user_id}/stats", tags=["阅读进度"])
def get_user_reading_stats(user_id: int):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    stats = recommender.reading_predictor.get_user_reading_stats(user_id)
    return stats


@app.get("/reading/{user_id}/schedule", tags=["阅读进度"])
def get_reading_schedule(user_id: int, daily_goal_pages: int = 30):
    user = data_store.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    schedule = recommender.reading_predictor.recommend_reading_schedule(user_id, daily_goal_pages)
    return schedule


@app.get("/books/{book_id}/summary", response_model=BookReviewSummary, tags=["书评摘要"])
def get_book_summary(book_id: int, force_regenerate: bool = False):
    book = data_store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    
    summary = recommender.review_summarizer.generate_summary(book_id, force_regenerate)
    return summary


@app.post("/books/summaries/batch", tags=["书评摘要"])
def batch_generate_summaries(book_ids: Optional[List[int]] = None):
    summaries = recommender.review_summarizer.batch_generate_summaries(book_ids)
    return {
        "generated_count": len(summaries),
        "summaries": summaries
    }


@app.get("/books/{book_id}/reading-guide", tags=["书评摘要"])
def get_reading_guide(book_id: int):
    book = data_store.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    
    guide = recommender.review_summarizer.get_reading_guide(book_id)
    return guide


@app.get("/books/compare", tags=["书评摘要"])
def compare_books(book_ids: List[int] = Query(...)):
    if len(book_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2本书才能比较")
    
    for bid in book_ids:
        if not data_store.get_book(bid):
            raise HTTPException(status_code=404, detail=f"书籍 {bid} 不存在")
    
    comparison = recommender.review_summarizer.get_comparative_summary(book_ids)
    return comparison


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
