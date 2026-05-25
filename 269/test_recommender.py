import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import DataGenerator
from recommenders import (
    CollaborativeFilteringRecommender,
    ContentFilteringRecommender,
    HybridRecommender
)


def test_data_generation():
    print("=" * 60)
    print("Testing Data Generation")
    print("=" * 60)
    
    data_gen = DataGenerator(seed=42)
    songs = data_gen.generate_songs(num_songs=50)
    users = data_gen.generate_users(num_users=20)
    behaviors = data_gen.generate_behaviors(
        min_behaviors_per_user=5,
        max_behaviors_per_user=15
    )
    
    print(f"Generated {len(songs)} songs")
    print(f"Generated {len(users)} users")
    print(f"Generated {len(behaviors)} behaviors")
    
    ratings_df = data_gen.get_ratings_dataframe()
    print(f"Total ratings: {len(ratings_df)}")
    print(f"Unique users: {ratings_df['user_id'].nunique()}")
    print(f"Unique songs: {ratings_df['song_id'].nunique()}")
    print(f"Rating range: [{ratings_df['rating'].min():.2f}, {ratings_df['rating'].max():.2f}]")
    
    return data_gen, songs, users, ratings_df


def test_collaborative_filtering(ratings_df):
    print("\n" + "=" * 60)
    print("Testing Collaborative Filtering")
    print("=" * 60)
    
    cf = CollaborativeFilteringRecommender()
    metrics = cf.train(ratings_df, method="svd")
    print(f"Model trained - RMSE: {metrics['rmse']:.4f}, MAE: {metrics['mae']:.4f}")
    
    user_id = ratings_df["user_id"].iloc[0]
    all_song_ids = ratings_df["song_id"].unique().tolist()
    
    recommendations = cf.recommend_for_user(user_id, all_song_ids, top_n=5)
    print(f"\nTop 5 recommendations for {user_id}:")
    for song_id, score in recommendations:
        print(f"  {song_id}: {score:.4f}")
    
    return cf


def test_content_filtering(songs, ratings_df):
    print("\n" + "=" * 60)
    print("Testing Content-based Filtering")
    print("=" * 60)
    
    data_gen = DataGenerator()
    data_gen.songs = songs
    songs_df = data_gen.get_songs_dataframe()
    
    content = ContentFilteringRecommender()
    content.build_feature_matrix(songs_df)
    content.compute_similarity_matrix()
    print("Similarity matrix computed")
    
    song_id = songs[0].song_id
    similar_songs = content.get_song_similar_songs(song_id, top_n=5)
    print(f"\nTop 5 similar songs to {song_id}:")
    for sim_id, score in similar_songs:
        print(f"  {sim_id}: {score:.4f}")
    
    user_id = ratings_df["user_id"].iloc[0]
    user_ratings = ratings_df[ratings_df["user_id"] == user_id]
    liked_songs = user_ratings[user_ratings["rating"] >= 3.5]["song_id"].tolist()
    all_song_ids = [s.song_id for s in songs]
    
    print(f"\nUser {user_id} liked {len(liked_songs)} songs")
    if liked_songs:
        recs = content.recommend_for_user(liked_songs, all_song_ids, top_n=5)
        print("Content-based recommendations:")
        for song_id, score in recs:
            print(f"  {song_id}: {score:.4f}")
    
    return content


def test_hybrid_recommender(songs, ratings_df, cf, content):
    print("\n" + "=" * 60)
    print("Testing Hybrid Recommender")
    print("=" * 60)
    
    hybrid = HybridRecommender(cf, content, cf_weight=0.5, content_weight=0.5)
    hybrid.set_songs(songs)
    
    user_id = ratings_df["user_id"].iloc[0]
    all_song_ids = [s.song_id for s in songs]
    
    recommendations = hybrid.hybrid_recommend(
        user_id=user_id,
        ratings_df=ratings_df,
        top_n=5,
        use_bandit=True,
        use_cache=False
    )
    
    print(f"\nHybrid recommendations for {user_id}:")
    print(f"{'Rank':<5} {'Song ID':<10} {'Score':<8} {'Source':<15} {'Reason'}")
    print("-" * 80)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i:<5} {rec.song_id:<10} {rec.score:<8.4f} {rec.source:<15} {rec.reason[:50]}...")
    
    return hybrid


def main():
    try:
        data_gen, songs, users, ratings_df = test_data_generation()
        cf = test_collaborative_filtering(ratings_df)
        content = test_content_filtering(songs, ratings_df)
        hybrid = test_hybrid_recommender(songs, ratings_df, cf, content)
        
        print("\n" + "=" * 60)
        print("All tests passed! ✅")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
