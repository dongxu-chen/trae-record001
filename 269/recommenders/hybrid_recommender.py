import random
import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter
from config import settings
from data.models import Song, RecommendationItem
from .collaborative_filtering import CollaborativeFilteringRecommender
from .content_filtering import ContentFilteringRecommender
from .multimodal import MultimodalSimilarity
from .bandit import EpsilonGreedyBandit
from .cache import RecommendationCache
from .realtime_feedback import RealTimeFeedbackUpdater, SkipPenaltyManager


class HybridRecommender:
    def __init__(self, 
                 cf_recommender: CollaborativeFilteringRecommender,
                 content_recommender: ContentFilteringRecommender,
                 multimodal: MultimodalSimilarity = None,
                 cache: RecommendationCache = None,
                 base_cf_weight: float = None,
                 base_content_weight: float = None,
                 multimodal_weight: float = 0.3):
        self.cf = cf_recommender
        self.content = content_recommender
        self.multimodal = multimodal
        self.cache = cache or RecommendationCache()
        self.base_cf_weight = base_cf_weight or settings.CF_WEIGHT
        self.base_content_weight = base_content_weight or settings.CONTENT_WEIGHT
        self.multimodal_weight = multimodal_weight
        
        self.bandit = EpsilonGreedyBandit()
        self.feedback_updater = RealTimeFeedbackUpdater()
        self.skip_penalty = SkipPenaltyManager()
        
        self.songs_map: Dict[str, Song] = {}
        self.user_activity: Dict[str, Dict] = defaultdict(lambda: {
            "total_plays": 0,
            "unique_songs": set(),
            "first_visit": None,
            "last_visit": None
        })
        self.user_bandit_epsilon: Dict[str, float] = defaultdict(lambda: settings.BANDIT_EPSILON)
    
    def set_songs(self, songs: List[Song]):
        self.songs_map = {song.song_id: song for song in songs}
    
    def set_multimodal(self, multimodal: MultimodalSimilarity):
        self.multimodal = multimodal
    
    def update_user_activity(self, user_id: str, song_id: str):
        activity = self.user_activity[user_id]
        activity["total_plays"] += 1
        activity["unique_songs"].add(song_id)
        if activity["first_visit"] is None:
            activity["first_visit"] = datetime.now()
        activity["last_visit"] = datetime.now()
    
    def calculate_user_activity_score(self, user_id: str) -> float:
        activity = self.user_activity[user_id]
        total_plays = activity["total_plays"]
        unique_count = len(activity["unique_songs"])
        
        plays_score = min(total_plays / 50, 1.0)
        unique_score = min(unique_count / 20, 1.0)
        
        activity_score = (plays_score * 0.6 + unique_score * 0.4)
        return min(activity_score, 1.0)
    
    def get_dynamic_weights(self, user_id: str) -> Tuple[float, float]:
        activity_score = self.calculate_user_activity_score(user_id)
        
        cf_weight = 0.2 + activity_score * 0.6
        content_weight = 0.8 - activity_score * 0.6
        
        total = cf_weight + content_weight
        return cf_weight / total, content_weight / total
    
    def calculate_decayed_epsilon(self, user_id: str, 
                            decay_rate: float = 0.05,
                            min_epsilon: float = 0.02) -> float:
        activity_score = self.calculate_user_activity_score(user_id)
        
        initial_epsilon = settings.BANDIT_EPSILON
        decayed_epsilon = initial_epsilon * math.exp(-decay_rate * activity_score * 10)
        decayed_epsilon = max(decayed_epsilon, min_epsilon)
        
        self.user_bandit_epsilon[user_id] = decayed_epsilon
        return decayed_epsilon
    
    def _get_user_liked_songs(self, user_id: str, ratings_df) -> List[str]:
        user_ratings = ratings_df[ratings_df["user_id"] == user_id]
        liked_songs = user_ratings[user_ratings["rating"] >= 3.5]["song_id"].tolist()
        return liked_songs
    
    def _normalize_scores(self, scores: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        if not scores:
            return []
        
        values = [s for _, s in scores]
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return [(song_id, 0.5) for song_id, _ in scores]
        
        normalized = []
        for song_id, score in scores:
            normalized_score = (score - min_val) / (max_val - min_val)
            normalized.append((song_id, round(normalized_score, 4)))
        
        return normalized
    
    def recommend_cf(self, user_id: str, all_song_ids: List[str], 
                    top_n: int = 50) -> List[Tuple[str, float]]:
        cf_scores = self.cf.recommend_for_user(user_id, all_song_ids, top_n=top_n)
        return self._normalize_scores(cf_scores)
    
    def recommend_content(self, user_id: str, user_liked_songs: List[str],
                         all_song_ids: List[str], 
                         top_n: int = 50) -> List[Tuple[str, float]]:
        content_scores = self.content.recommend_for_user(
            user_liked_songs, all_song_ids, top_n=top_n
        )
        return self._normalize_scores(content_scores)
    
    def recommend_multimodal(self, user_liked_songs: List[str],
                            all_song_ids: List[str],
                            top_n: int = 50) -> List[Tuple[str, float]]:
        if self.multimodal is None or self.multimodal.similarity_matrix is None:
            return []
        
        liked_indices = []
        for song_id in user_liked_songs:
            if song_id in self.multimodal.song_id_to_idx:
                liked_indices.append(self.multimodal.song_id_to_idx[song_id])
        
        if not liked_indices:
            return []
        
        scores = self.multimodal.similarity_matrix[liked_indices].mean(axis=0)
        
        candidate_songs = []
        for song_id in all_song_ids:
            if song_id not in user_liked_songs and song_id in self.multimodal.song_id_to_idx:
                song_idx = self.multimodal.song_id_to_idx[song_id]
                candidate_songs.append((song_id, round(scores[song_idx], 4)))
        
        candidate_songs.sort(key=lambda x: x[1], reverse=True)
        return candidate_songs[:top_n]
    
    def _analyze_user_preferences(self, user_liked_songs: List[str]) -> Dict:
        genre_counter = Counter()
        artist_counter = Counter()
        decades = Counter()
        
        for song_id in user_liked_songs:
            if song_id in self.songs_map:
                song = self.songs_map[song_id]
                genre_counter[song.genre] += 1
                artist_counter[song.artist] += 1
                decade = (song.year // 10) * 10
                decades[decade] += 1
        
        return {
            "genres": genre_counter.most_common(),
            "artists": artist_counter.most_common(),
            "decades": decades.most_common()
        }
    
    def generate_multi_dimension_reason(self, song_id: str, 
                                user_liked_songs: List[str],
                                cf_scores: Dict[str, float],
                                user_prefs: Dict,
                                multimodal_reasons: List[str] = None) -> List[str]:
        reasons = []
        
        if song_id not in self.songs_map:
            return reasons
        
        song = self.songs_map[song_id]
        
        genre_reasons = [
            f"您喜爱的{song.genre}曲风",
            f"属于您常听的{song.genre}类型",
            f"{song.genre}风格，符合您的音乐品味",
            f"典型的{song.genre}佳作"
        ]
        
        top_genres = [g for g, _ in user_prefs["genres"][:3]]
        if song.genre in top_genres:
            reasons.append(random.choice(genre_reasons))
        
        song_decade = (song.year // 10) * 10
        decade_reasons = [
            f"{song_decade}年代经典",
            f"{song_decade}年代金曲",
            f"来自{song_decade}年代的好歌",
            f"{song_decade}s年代代表作"
        ]
        top_decades = [d for d, _ in user_prefs["decades"]]
        if song_decade in top_decades:
            reasons.append(random.choice(decade_reasons))
        
        if user_prefs["artists"]:
            top_artist, top_artist_count = user_prefs["artists"][0]
            if song.artist == top_artist and top_artist_count >= 3:
                artist_reasons = [
                    f"您最爱的歌手{song.artist}",
                    f"{song.artist}的新歌",
                    f"{song.artist}又一力作",
                    f"来自{song.artist}"
                ]
                reasons.append(random.choice(artist_reasons))
        
        if len(user_prefs["artists"]) >= 2:
            similar_artists = [a for a, _ in user_prefs["artists"][:5]]
            if song.artist in similar_artists[1:]:
                reasons.append(f"与您喜爱的{song.artist}也很对味")
        
        cf_score = cf_scores.get(song_id, 0)
        if cf_score > 0.75:
            cf_reasons = [
                "与您兴趣相投的用户也在听",
                "同好用户的选择",
                "品味相近的用户推荐",
                "和您听感相似的用户喜欢"
            ]
            reasons.append(random.choice(cf_reasons))
        elif cf_score > 0.6:
            reasons.append("不少用户喜欢这首歌")
        
        if song.popularity > 0.85:
            popularity_reasons = [
                "近期热门",
                "排行榜热门歌曲",
                "正在流行",
                "人气飙升"
            ]
            reasons.append(random.choice(popularity_reasons))
        elif song.popularity > 0.7:
            reasons.append("备受好评")
        
        song_years = [s.year for s in self.songs_map.values() if s.artist == song.artist]
        if len(song_years) >= 3 and song.year == max(song_years):
            reasons.append(f"{song.artist}最新作品")
        
        if multimodal_reasons:
            reasons.extend(multimodal_reasons)
        
        return reasons
    
    def hybrid_recommend(self, user_id: str, ratings_df, 
                        top_n: int = 10,
                        use_bandit: bool = True,
                        use_cache: bool = True,
                        use_multimodal: bool = True) -> List[RecommendationItem]:
        if use_cache:
            cached = self.cache.get_recommendations(user_id)
            if cached:
                return [RecommendationItem(**item) for item in cached]
        
        all_song_ids = list(self.songs_map.keys())
        user_liked_songs = self._get_user_liked_songs(user_id, ratings_df)
        
        for song_id in user_liked_songs:
            self.update_user_activity(user_id, song_id)
        
        cf_weight, content_weight = self.get_dynamic_weights(user_id)
        
        cf_scores = dict(self.recommend_cf(user_id, all_song_ids, top_n=top_n*5))
        content_scores = dict(self.recommend_content(user_id, user_liked_songs, all_song_ids, top_n=top_n*5))
        
        multimodal_scores = {}
        multimodal_reasons_map = {}
        if use_multimodal and self.multimodal:
            multimodal_raw = dict(self.recommend_multimodal(user_liked_songs, all_song_ids, top_n=top_n*5))
            for song_id, score in multimodal_raw.items():
                if song_id in self.songs_map:
                    mm_reasons = self.multimodal.get_multimodal_reason(song_id, user_liked_songs)
                    if mm_reasons:
                        multimodal_reasons_map[song_id] = mm_reasons
            multimodal_scores = multimodal_raw
        
        all_candidates = set(cf_scores.keys()) | set(content_scores.keys()) | set(multimodal_scores.keys())
        
        hybrid_scores = {}
        for song_id in all_candidates:
            cf_score = cf_scores.get(song_id, 0)
            content_score = content_scores.get(song_id, 0)
            mm_score = multimodal_scores.get(song_id, 0)
            
            total_weight = cf_weight + content_weight + (self.multimodal_weight if mm_score > 0 else 0)
            hybrid_score = (cf_weight * cf_score + content_weight * content_score + 
                          (self.multimodal_weight * mm_score if mm_score > 0 else 0)) / total_weight
            
            hybrid_scores[song_id] = round(hybrid_score, 4)
        
        hybrid_scores = self.feedback_updater.calculate_adjusted_scores(
            user_id, hybrid_scores, self.songs_map
        )
        
        candidate_dicts = [{"song_id": sid, "score": score, 
                            "genre": self.songs_map[sid].genre if sid in self.songs_map else ""}
                           for sid, score in hybrid_scores.items()]
        penalized = self.skip_penalty.apply_penalties(user_id, candidate_dicts)
        hybrid_scores = {item["song_id"]: item["adjusted_score"] for item in penalized}
        
        if use_bandit:
            current_epsilon = self.calculate_decayed_epsilon(user_id)
            self.bandit.epsilon = current_epsilon
            
            exploit_candidates = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
            top_candidates = {sid: score for sid, score in exploit_candidates[:top_n*2]}
            
            explore_candidates = [sid for sid in all_song_ids if sid not in top_candidates]
            
            selected = self.bandit.select_arms(
                list(top_candidates.keys()) + explore_candidates,
                top_n,
                exploit_scores={**top_candidates, **{sid: 0.1 for sid in explore_candidates}}
            )
            
            final_scores = [(sid, hybrid_scores.get(sid, 0.1)) for sid in selected]
        else:
            final_scores = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        user_prefs = self._analyze_user_preferences(user_liked_songs)
        
        recommendations = []
        for song_id, score in final_scores:
            if song_id in self.songs_map:
                song = self.songs_map[song_id]
                mm_reasons = multimodal_reasons_map.get(song_id, [])
                reason_list = self.generate_multi_dimension_reason(
                    song_id, user_liked_songs, cf_scores, user_prefs, mm_reasons
                )
                
                if not reason_list:
                    reason_list = ["为您精选", "值得一听"]
                
                reason = "；".join(reason_list[:3])
                source = self._determine_source(song_id, cf_scores, content_scores, 
                                              multimodal_scores, cf_weight, content_weight)
                
                recommendations.append(RecommendationItem(
                    song_id=song_id,
                    title=song.title,
                    artist=song.artist,
                    genre=song.genre,
                    year=song.year,
                    score=score,
                    reason=reason,
                    source=source
                ))
        
        if use_cache:
            self.cache.set_recommendations(
                user_id,
                [rec.model_dump() for rec in recommendations]
            )
        
        return recommendations
    
    def _determine_source(self, song_id: str, cf_scores: Dict[str, float],
                         content_scores: Dict[str, float],
                         multimodal_scores: Dict[str, float],
                         cf_weight: float, content_weight: float) -> str:
        cf_score = cf_scores.get(song_id, 0)
        content_score = content_scores.get(song_id, 0)
        mm_score = multimodal_scores.get(song_id, 0)
        
        cf_contribution = cf_score * cf_weight
        content_contribution = content_score * content_weight
        mm_contribution = mm_score * self.multimodal_weight
        
        contributions = [
            ("collaborative", cf_contribution),
            ("content", content_contribution),
            ("multimodal", mm_contribution)
        ]
        positive_contributions = [(name, val) for name, val in contributions if val > 0]
        
        if len(positive_contributions) >= 2:
            return "hybrid"
        elif len(positive_contributions) == 1:
            return positive_contributions[0][0]
        else:
            return "explore"
    
    def record_user_action(self, user_id: str, song_id: str, action: str, **kwargs):
        song_info = {}
        if song_id in self.songs_map:
            song = self.songs_map[song_id]
            song_info = {
                "genre": song.genre,
                "artist": song.artist,
                "year": song.year
            }
        
        self.feedback_updater.record_action(user_id, song_id, action, song_info=song_info, **kwargs)
        self.update_user_activity(user_id, song_id)
        
        if song_id in self.songs_map:
            if action == "skip":
                self.skip_penalty.record_skip(user_id, self.songs_map[song_id].genre)
            elif action in ["play_complete", "like"]:
                self.skip_penalty.record_play(user_id, self.songs_map[song_id].genre)
        
        reward_map = {
            "like": 5.0,
            "play_complete": 3.5,
            "play_partial": 2.0,
            "skip": 1.0,
            "dislike": 0.0
        }
        reward = reward_map.get(action, 2.5)
        self.bandit.update(song_id, reward)
        
        self.cache.invalidate_user(user_id)
    
    def update_feedback(self, user_id: str, song_id: str, reward: float):
        self.bandit.update(song_id, reward)
        self.update_user_activity(user_id, song_id)
        self.cache.invalidate_user(user_id)
    
    def get_user_skip_stats(self, user_id: str) -> Dict:
        return self.feedback_updater.get_user_skip_statistics(user_id)
    
    def recommend_similar_songs(self, song_id: str, 
                               top_n: int = 10,
                               use_multimodal: bool = True) -> List[RecommendationItem]:
        similar_songs = self.content.get_song_similar_songs(song_id, top_n=top_n*2)
        
        if use_multimodal and self.multimodal:
            mm_similar = dict(self.multimodal.get_similar_songs(song_id, top_n=top_n*2))
            combined = {}
            for sid, score in similar_songs:
                combined[sid] = score * 0.6
            for sid, score in mm_similar.items():
                combined[sid] = combined.get(sid, 0) + score * 0.4
            similar_songs = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        recommendations = []
        for sim_song_id, score in similar_songs[:top_n]:
            if sim_song_id in self.songs_map:
                song = self.songs_map[sim_song_id]
                original_song = self.songs_map.get(song_id)
                
                reason_templates = [
                    f"与《{original_song.title if original_song else '该歌曲'}》曲风相近",
                    f"类似《{original_song.title if original_song else '该歌曲'}》的好歌",
                    f"和《{original_song.title if original_song else '该歌曲'}》风格匹配"
                ]
                
                recommendations.append(RecommendationItem(
                    song_id=sim_song_id,
                    title=song.title,
                    artist=song.artist,
                    genre=song.genre,
                    year=song.year,
                    score=score,
                    reason=random.choice(reason_templates),
                    source="content"
                ))
        
        return recommendations
    
    def get_explore_recommendations(self, user_id: str, 
                                    top_n: int = 5) -> List[RecommendationItem]:
        all_song_ids = list(self.songs_map.keys())
        user_liked_songs = self._get_user_liked_songs_from_activity(user_id)
        
        explore_songs = [sid for sid in all_song_ids if sid not in user_liked_songs]
        explore_songs = random.sample(explore_songs, min(top_n * 3, len(explore_songs)))
        
        recommendations = []
        for song_id in explore_songs[:top_n]:
            if song_id in self.songs_map:
                song = self.songs_map[song_id]
                
                explore_reasons = [
                    "发现新声音",
                    "拓展你的音乐版图",
                    "试试新歌",
                    "新鲜推荐",
                    "探索更多音乐"
                ]
                
                recommendations.append(RecommendationItem(
                    song_id=song_id,
                    title=song.title,
                    artist=song.artist,
                    genre=song.genre,
                    year=song.year,
                    score=0.5,
                    reason=random.choice(explore_reasons),
                    source="explore"
                ))
        
        return recommendations
    
    def _get_user_liked_songs_from_activity(self, user_id: str) -> List[str]:
        return list(self.user_activity[user_id]["unique_songs"])
    
    def get_user_profile(self, user_id: str) -> Dict:
        activity_score = self.calculate_user_activity_score(user_id)
        cf_weight, content_weight = self.get_dynamic_weights(user_id)
        current_epsilon = self.calculate_decayed_epsilon(user_id)
        
        activity = self.user_activity[user_id]
        skip_stats = self.feedback_updater.get_user_skip_statistics(user_id)
        pref_summary = self.feedback_updater.get_user_preference_summary(user_id)
        
        return {
            "user_id": user_id,
            "activity_score": round(activity_score, 4),
            "total_plays": activity["total_plays"],
            "unique_songs_count": len(activity["unique_songs"]),
            "cf_weight": round(cf_weight, 4),
            "content_weight": round(content_weight, 4),
            "multimodal_weight": self.multimodal_weight,
            "current_epsilon": round(current_epsilon, 4),
            "is_new_user": activity_score < 0.3,
            "skip_statistics": skip_stats,
            "realtime_preferences": pref_summary
        }
