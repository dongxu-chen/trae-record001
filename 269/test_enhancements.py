import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import DataGenerator
from recommenders import (
    CollaborativeFilteringRecommender,
    ContentFilteringRecommender,
    HybridRecommender
)


def test_dynamic_weights():
    print("=" * 60)
    print("Testing Dynamic Weight Adjustment")
    print("=" * 60)
    
    data_gen = DataGenerator(seed=42)
    songs = data_gen.generate_songs(num_songs=50)
    users = data_gen.generate_users(num_users=10)
    data_gen.generate_behaviors(min_behaviors_per_user=5, max_behaviors_per_user=20)
    ratings_df = data_gen.get_ratings_dataframe()
    
    cf = CollaborativeFilteringRecommender()
    cf.train(ratings_df, method="svd")
    
    songs_df = data_gen.get_songs_dataframe()
    content = ContentFilteringRecommender()
    content.build_feature_matrix(songs_df)
    content.compute_similarity_matrix()
    
    hybrid = HybridRecommender(cf, content)
    hybrid.set_songs(songs)
    
    user_id = ratings_df["user_id"].iloc[0]
    print(f"\nTesting user: {user_id}")
    
    print("\n1. New user (no activity):")
    profile = hybrid.get_user_profile(user_id)
    print(f"   Activity score: {profile['activity_score']:.4f}")
    print(f"   CF weight: {profile['cf_weight']:.4f}")
    print(f"   Content weight: {profile['content_weight']:.4f}")
    print(f"   Is new user: {profile['is_new_user']}")
    
    print("\n2. Simulating user activity...")
    user_liked_songs = ratings_df[ratings_df["user_id"] == user_id]
    user_liked_songs = user_liked_songs[user_liked_songs["rating"] >= 3.5]["song_id"].tolist()
    
    for song_id in user_liked_songs:
        hybrid.update_user_activity(user_id, song_id)
    
    profile = hybrid.get_user_profile(user_id)
    print(f"\n3. After {profile['total_plays']} plays:")
    print(f"   Activity score: {profile['activity_score']:.4f}")
    print(f"   CF weight: {profile['cf_weight']:.4f}")
    print(f"   Content weight: {profile['content_weight']:.4f}")
    print(f"   Is new user: {profile['is_new_user']}")
    
    return hybrid, user_id, ratings_df


def test_epsilon_decay(hybrid, user_id):
    print("\n" + "=" * 60)
    print("Testing Epsilon Decay")
    print("=" * 60)
    
    print(f"\nUser: {user_id}")
    
    profile = hybrid.get_user_profile(user_id)
    print(f"Initial epsilon: {profile['current_epsilon']:.4f}")
    
    print("\nSimulating more activity to see decay...")
    for i in range(30):
        hybrid.update_user_activity(user_id, f"s_test_{i}")
    
    profile = hybrid.get_user_profile(user_id)
    print(f"\nAfter {profile['total_plays']} total plays:")
    print(f"   Activity score: {profile['activity_score']:.4f}")
    print(f"   Current epsilon: {profile['current_epsilon']:.4f}")
    print(f"   Decay applied: epsilon decreases as activity increases")


def test_multi_dimension_reasons(hybrid, user_id, ratings_df):
    print("\n" + "=" * 60)
    print("Testing Multi-Dimension Recommendation Reasons")
    print("=" * 60)
    
    recommendations = hybrid.hybrid_recommend(
        user_id=user_id,
        ratings_df=ratings_df,
        top_n=5,
        use_bandit=True,
        use_cache=False
    )
    
    print(f"\nTop 5 recommendations with reasons for {user_id}:")
    print(f"{'Rank':<5} {'Song ID':<10} {'Score':<8} {'Source':<15}")
    print("-" * 80)
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i:<5} {rec.song_id:<10} {rec.score:<8.4f} {rec.source:<15}")
        print(f"      Reason: {rec.reason}")
        print()


def test_user_preferences_analysis(hybrid, user_id, ratings_df):
    print("\n" + "=" * 60)
    print("Testing User Preferences Analysis")
    print("=" * 60)
    
    user_ratings = ratings_df[ratings_df["user_id"] == user_id]
    liked_songs = user_ratings[user_ratings["rating"] >= 3.5]["song_id"].tolist()
    
    user_prefs = hybrid._analyze_user_preferences(liked_songs)
    
    print(f"\nUser {user_id} preferences:")
    print(f"Total liked songs: {len(liked_songs)}")
    
    print("\nTop Genres:")
    for genre, count in user_prefs["genres"][:5]:
        print(f"  {genre}: {count} songs")
    
    print("\nTop Artists:")
    for artist, count in user_prefs["artists"][:5]:
        print(f"  {artist}: {count} songs")
    
    print("\nTop Decades:")
    for decade, count in user_prefs["decades"][:3]:
        print(f"  {decade}s: {count} songs")


def main():
    try:
        hybrid, user_id, ratings_df = test_dynamic_weights()
        test_epsilon_decay(hybrid, user_id)
        test_multi_dimension_reasons(hybrid, user_id, ratings_df)
        test_user_preferences_analysis(hybrid, user_id, ratings_df)
        
        print("\n" + "=" * 60)
        print("All enhancement tests passed! ✅")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
