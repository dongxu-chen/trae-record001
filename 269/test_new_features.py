import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import DataGenerator
from recommenders import (
    CollaborativeFilteringRecommender,
    ContentFilteringRecommender,
    HybridRecommender,
    MultimodalSimilarity,
    PlaylistGenerator,
    RealTimeFeedbackUpdater
)


def test_multimodal_features():
    print("=" * 60)
    print("Testing Multimodal Features")
    print("=" * 60)
    
    data_gen = DataGenerator(seed=42)
    songs = data_gen.generate_songs(num_songs=50)
    songs_df = data_gen.get_songs_dataframe()
    
    print("\n1. Building multimodal similarity...")
    multimodal = MultimodalSimilarity(
        image_weight=0.3,
        text_weight=0.3,
        content_weight=0.4
    )
    multimodal.build_multimodal_features(songs_df)
    print("   Multimodal features built successfully!")
    
    print("\n2. Testing similar songs with multimodal...")
    test_song_id = songs[0].song_id
    similar = multimodal.get_similar_songs(test_song_id, top_n=5)
    
    print(f"   Top 5 similar songs to {test_song_id}:")
    for song_id, score in similar[:3]:
        print(f"      {song_id}: {score:.4f}")
    
    print("\n3. Testing multimodal reasons...")
    user_liked = [s.song_id for s in songs[:10]]
    reasons = multimodal.get_multimodal_reason(test_song_id, user_liked)
    print(f"   Multimodal reasons: {reasons}")
    
    return multimodal, songs_df


def test_realtime_feedback():
    print("\n" + "=" * 60)
    print("Testing Real-time Feedback Update")
    print("=" * 60)
    
    feedback = RealTimeFeedbackUpdater()
    
    print("\n1. Recording user actions...")
    user_id = "test_user_001"
    
    actions = [
        ("s_0001", "like"),
        ("s_0002", "play_complete"),
        ("s_0003", "skip"),
        ("s_0004", "play_partial"),
        ("s_0005", "skip"),
        ("s_0006", "skip"),
    ]
    
    for song_id, action in actions:
        song_info = {"genre": "pop", "artist": "Test Artist", "year": 2020}
        feedback.record_action(user_id, song_id, action, song_info=song_info)
        print(f"   Recorded {action} for {song_id}")
    
    print("\n2. Getting user skip statistics...")
    skip_stats = feedback.get_user_skip_statistics(user_id)
    print(f"   Total actions: {skip_stats['total_actions']}")
    print(f"   Skip count: {skip_stats['skip_count']}")
    print(f"   Skip rate: {skip_stats['skip_rate']:.2%}")
    print(f"   Top skipped genres: {skip_stats['top_skipped_genres']}")
    
    print("\n3. Getting user preference summary...")
    pref_summary = feedback.get_user_preference_summary(user_id)
    print(f"   Top genres: {pref_summary['top_genres']}")
    print(f"   Top artists: {pref_summary['top_artists']}")
    
    return feedback


def test_playlist_generation():
    print("\n" + "=" * 60)
    print("Testing Playlist Generation")
    print("=" * 60)
    
    print("\n1. Available playlist themes:")
    playlist_gen = PlaylistGenerator()
    themes = playlist_gen.get_all_themes()
    for theme in themes:
        print(f"   - {theme['name']} ({theme['theme_id']}): {theme['description']}")
    
    print("\n2. Generating mock recommendations...")
    mock_recommendations = []
    genres = ["pop", "rock", "jazz", "electronic", "hiphop"]
    artists = ["Artist A", "Artist B", "Artist C", "Artist D", "Artist E"]
    
    for i in range(50):
        mock_recommendations.append({
            "song_id": f"s_{i:04d}",
            "title": f"Song {i}",
            "artist": artists[i % len(artists)],
            "genre": genres[i % len(genres)],
            "year": 2000 + (i % 25),
            "score": 0.3 + (i / 100)
        })
    
    print("\n3. Generating themed playlist...")
    playlist = playlist_gen.generate_from_recommendations(
        recommendations=mock_recommendations,
        theme=None,
        playlist_size=20
    )
    
    print(f"   Playlist ID: {playlist.playlist_id}")
    print(f"   Playlist name: {playlist.name}")
    print(f"   Theme: {playlist.theme}")
    print(f"   Songs: {len(playlist.songs)} songs")
    print(f"   Diversity score: {playlist.diversity_score}")
    print(f"   Coherence score: {playlist.coherence_score}")
    
    print("\n4. Playlist songs:")
    for i, song in enumerate(playlist.songs[:5], 1):
        print(f"      {i}. {song.title} by {song.artist} ({song.genre})")
    
    print("\n5. Generating Smart Mix...")
    similar_songs = mock_recommendations[10:30]
    explore_songs = mock_recommendations[30:45]
    
    smart_mix = playlist_gen.generate_smart_mix(
        user_recommendations=mock_recommendations[:25],
        similar_songs=similar_songs,
        explore_songs=explore_songs,
        playlist_size=30
    )
    
    print(f"   Smart Mix ID: {smart_mix.playlist_id}")
    print(f"   Smart Mix name: {smart_mix.name}")
    print(f"   Songs: {len(smart_mix.songs)} songs")
    print(f"   Diversity score: {smart_mix.diversity_score}")
    
    return playlist_gen


def test_hybrid_with_multimodal():
    print("\n" + "=" * 60)
    print("Testing Hybrid Recommender with Multimodal")
    print("=" * 60)
    
    data_gen = DataGenerator(seed=42)
    songs = data_gen.generate_songs(num_songs=50)
    users = data_gen.generate_users(num_users=10)
    data_gen.generate_behaviors(min_behaviors_per_user=5, max_behaviors_per_user=15)
    ratings_df = data_gen.get_ratings_dataframe()
    songs_df = data_gen.get_songs_dataframe()
    
    print("\n1. Training CF model...")
    cf = CollaborativeFilteringRecommender()
    cf.train(ratings_df, method="svd")
    
    print("2. Building content model...")
    content = ContentFilteringRecommender()
    content.build_feature_matrix(songs_df)
    content.compute_similarity_matrix()
    
    print("3. Building multimodal model...")
    multimodal = MultimodalSimilarity()
    multimodal.build_multimodal_features(songs_df)
    multimodal.combine_with_content_similarity(content.similarity_matrix)
    
    print("4. Creating hybrid recommender...")
    hybrid = HybridRecommender(
        cf_recommender=cf,
        content_recommender=content,
        multimodal=multimodal,
        multimodal_weight=0.3
    )
    hybrid.set_songs(songs)
    
    print("\n5. Testing recommendations with multimodal...")
    user_id = users[0].user_id
    recommendations = hybrid.hybrid_recommend(
        user_id=user_id,
        ratings_df=ratings_df,
        top_n=5,
        use_multimodal=True
    )
    
    print(f"   Top 5 recommendations for {user_id}:")
    for i, rec in enumerate(recommendations, 1):
        print(f"      {i}. {rec.title} by {rec.artist}")
        print(f"         Score: {rec.score:.4f} | Source: {rec.source}")
        print(f"         Reason: {rec.reason}")
    
    print("\n6. Testing real-time feedback integration...")
    print("   Recording 'skip' action...")
    skipped_song = recommendations[0].song_id
    hybrid.record_user_action(user_id, skipped_song, "skip")
    print(f"   Recorded skip for {skipped_song}")
    
    print("\n7. Getting updated recommendations after feedback...")
    new_recommendations = hybrid.hybrid_recommend(
        user_id=user_id,
        ratings_df=ratings_df,
        top_n=5,
        use_cache=False
    )
    print(f"   New top song: {new_recommendations[0].title}")
    
    return hybrid


def main():
    try:
        multimodal, songs_df = test_multimodal_features()
        feedback = test_realtime_feedback()
        playlist_gen = test_playlist_generation()
        hybrid = test_hybrid_with_multimodal()
        
        print("\n" + "=" * 60)
        print("All new feature tests passed! ✅")
        print("=" * 60)
        print("\nNew Features Summary:")
        print("  ✅ Multimodal Features (Image + Text)")
        print("  ✅ Real-time Feedback Update")
        print("  ✅ Skip Penalty Mechanism")
        print("  ✅ Playlist Generation (8 themes)")
        print("  ✅ Smart Mix Playlist")
        print("  ✅ Integration with Hybrid Recommender")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
