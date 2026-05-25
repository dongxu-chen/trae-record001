import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime
from pydantic import BaseModel


class PlaylistTheme(BaseModel):
    theme_id: str
    name: str
    description: str
    keywords: List[str]
    target_genres: List[str]
    mood: str
    energy_level: str


class PlaylistItem(BaseModel):
    song_id: str
    title: str
    artist: str
    genre: str
    year: int
    reason: str


class GeneratedPlaylist(BaseModel):
    playlist_id: str
    name: str
    description: str
    theme: str
    songs: List[PlaylistItem]
    generated_at: datetime
    diversity_score: float
    coherence_score: float


class PlaylistGenerator:
    def __init__(self):
        self.themes = self._init_themes()
    
    def _init_themes(self) -> List[PlaylistTheme]:
        return [
            PlaylistTheme(
                theme_id="chill_vibes",
                name="Chill Vibes",
                description="放松心情的轻音乐",
                keywords=["chill", "relax", "calm", "peaceful"],
                target_genres=["jazz", "classical", "pop"],
                mood="calm",
                energy_level="low"
            ),
            PlaylistTheme(
                theme_id="workout_hype",
                name="Workout Hype",
                description="运动健身专属能量歌单",
                keywords=["workout", "energy", "hype", "gym"],
                target_genres=["hiphop", "electronic", "rock"],
                mood="energetic",
                energy_level="high"
            ),
            PlaylistTheme(
                theme_id="late_night",
                name="Late Night",
                description="深夜专属抒情歌单",
                keywords=["night", "late", "moody", "emotional"],
                target_genres=["rnb", "pop", "jazz"],
                mood="melancholic",
                energy_level="low"
            ),
            PlaylistTheme(
                theme_id="retro_classics",
                name="Retro Classics",
                description="经典老歌回味",
                keywords=["retro", "classic", "old", "vintage"],
                target_genres=["rock", "pop", "jazz"],
                mood="nostalgic",
                energy_level="medium"
            ),
            PlaylistTheme(
                theme_id="party_mix",
                name="Party Mix",
                description="派对狂欢必备",
                keywords=["party", "dance", "club", "fun"],
                target_genres=["electronic", "pop", "hiphop"],
                mood="happy",
                energy_level="high"
            ),
            PlaylistTheme(
                theme_id="focus_flow",
                name="Focus Flow",
                description="专注工作学习背景音",
                keywords=["focus", "concentrate", "study", "work"],
                target_genres=["classical", "electronic", "jazz"],
                mood="focused",
                energy_level="medium"
            ),
            PlaylistTheme(
                theme_id="mood_booster",
                name="Mood Booster",
                description="心情提升正能量歌单",
                keywords=["happy", "positive", "upbeat", "cheer"],
                target_genres=["pop", "rock", "country"],
                mood="happy",
                energy_level="high"
            ),
            PlaylistTheme(
                theme_id="discovery",
                name="Discovery Mix",
                description="探索新音乐",
                keywords=["discover", "new", "explore", "fresh"],
                target_genres=[],
                mood="adventurous",
                energy_level="mixed"
            )
        ]
    
    def match_theme(self, user_preferences: Dict) -> List[PlaylistTheme]:
        genre_prefs = user_preferences.get("genres", {})
        mood_prefs = user_preferences.get("mood", "")
        
        theme_scores = []
        
        for theme in self.themes:
            score = 0
            
            if theme.target_genres:
                for genre in theme.target_genres:
                    if genre in genre_prefs:
                        score += genre_prefs[genre] * 2
            
            if mood_prefs and mood_prefs in theme.mood:
                score += 3
            
            if score > 0:
                theme_scores.append((theme, score))
        
        theme_scores.sort(key=lambda x: x[1], reverse=True)
        
        if not theme_scores:
            matched = random.sample(self.themes, min(3, len(self.themes)))
            return matched
        
        return [theme for theme, _ in theme_scores[:3]]
    
    def detect_theme_from_recommendations(self, recommendations: List[Dict]) -> PlaylistTheme:
        genre_counter = defaultdict(int)
        year_counter = defaultdict(int)
        moods = []
        
        for rec in recommendations:
            genre = rec.get("genre", "")
            year = rec.get("year", 2000)
            
            genre_counter[genre] += 1
            decade = (year // 10) * 10
            year_counter[decade] += 1
            
            if rec.get("score", 0) > 0.8:
                moods.append("happy")
            elif rec.get("score", 0) < 0.4:
                moods.append("calm")
        
        top_genre = max(genre_counter.items(), key=lambda x: x[1])[0] if genre_counter else "pop"
        top_decade = max(year_counter.items(), key=lambda x: x[1])[0] if year_counter else 2020
        
        for theme in self.themes:
            if top_genre in theme.target_genres:
                if top_decade < 2000 and "retro" in theme.theme_id:
                    return theme
                if theme.energy_level == "high" and len([m for m in moods if m == "happy"]) > len(recommendations) // 2:
                    return theme
        
        return random.choice(self.themes)
    
    def calculate_diversity(self, songs: List[Dict]) -> float:
        if len(songs) < 2:
            return 1.0
        
        genres = set()
        artists = set()
        decades = set()
        
        for song in songs:
            genres.add(song.get("genre", ""))
            artists.add(song.get("artist", ""))
            decade = (song.get("year", 2000) // 10) * 10
            decades.add(decade)
        
        genre_diversity = min(len(genres) / 5, 1.0)
        artist_diversity = min(len(artists) / len(songs), 1.0)
        decade_diversity = min(len(decades) / 3, 1.0)
        
        diversity = (genre_diversity * 0.4 + artist_diversity * 0.4 + decade_diversity * 0.2)
        return round(diversity, 4)
    
    def calculate_coherence(self, songs: List[Dict], theme: PlaylistTheme) -> float:
        if not theme.target_genres:
            return 0.7
        
        matching_genres = sum(1 for song in songs 
                             if song.get("genre", "") in theme.target_genres)
        genre_coherence = matching_genres / len(songs) if songs else 0
        
        return round(genre_coherence, 4)
    
    def generate_from_recommendations(self, 
                                       recommendations: List[Dict],
                                       theme: Optional[PlaylistTheme] = None,
                                       playlist_size: int = 20,
                                       min_diversity: float = 0.3) -> GeneratedPlaylist:
        if theme is None:
            theme = self.detect_theme_from_recommendations(recommendations)
        
        selected_songs = []
        used_artists = set()
        used_genres = set()
        
        sorted_recs = sorted(recommendations, key=lambda x: x.get("score", 0), reverse=True)
        
        for rec in sorted_recs:
            if len(selected_songs) >= playlist_size:
                break
            
            artist = rec.get("artist", "")
            genre = rec.get("genre", "")
            
            if theme.target_genres and genre not in theme.target_genres:
                if len(selected_songs) > playlist_size * 0.8:
                    continue
            
            if artist in used_artists and len(selected_songs) < playlist_size * 0.7:
                continue
            
            selected_songs.append({
                "song_id": rec.get("song_id", ""),
                "title": rec.get("title", ""),
                "artist": artist,
                "genre": genre,
                "year": rec.get("year", 2000),
                "score": rec.get("score", 0.5),
                "reason": self._generate_playlist_reason(rec, theme)
            })
            
            used_artists.add(artist)
            used_genres.add(genre)
        
        while len(selected_songs) < playlist_size and len(sorted_recs) > len(selected_songs):
            for rec in sorted_recs:
                if len(selected_songs) >= playlist_size:
                    break
                if rec.get("song_id") not in [s["song_id"] for s in selected_songs]:
                    selected_songs.append({
                        "song_id": rec.get("song_id", ""),
                        "title": rec.get("title", ""),
                        "artist": rec.get("artist", ""),
                        "genre": rec.get("genre", ""),
                        "year": rec.get("year", 2000),
                        "score": rec.get("score", 0.5),
                        "reason": self._generate_playlist_reason(rec, theme)
                    })
        
        diversity = self.calculate_diversity(selected_songs)
        coherence = self.calculate_coherence(selected_songs, theme)
        
        if diversity < min_diversity:
            selected_songs = self._improve_diversity(selected_songs, recommendations, min_diversity)
            diversity = self.calculate_diversity(selected_songs)
        
        playlist_id = f"pl_{int(datetime.now().timestamp())}"
        
        return GeneratedPlaylist(
            playlist_id=playlist_id,
            name=f"{theme.name} - 为您精选",
            description=f"{theme.description}。基于您的听歌偏好智能生成。",
            theme=theme.theme_id,
            songs=[PlaylistItem(**song) for song in selected_songs],
            generated_at=datetime.now(),
            diversity_score=diversity,
            coherence_score=coherence
        )
    
    def _generate_playlist_reason(self, song: Dict, theme: PlaylistTheme) -> str:
        reasons = []
        
        if song.get("score", 0) > 0.7:
            reasons.append("高度匹配您的口味")
        elif song.get("score", 0) > 0.5:
            reasons.append("符合您的偏好")
        
        if theme.target_genres and song.get("genre") in theme.target_genres:
            reasons.append(f"适合{theme.name}")
        
        if not reasons:
            reasons.append("为您推荐")
        
        return "，".join(reasons)
    
    def _improve_diversity(self, songs: List[Dict], all_recommendations: List[Dict], 
                          target_diversity: float) -> List[Dict]:
        current_diversity = self.calculate_diversity(songs)
        
        if current_diversity >= target_diversity:
            return songs
        
        genre_count = defaultdict(int)
        for song in songs:
            genre_count[song.get("genre", "")] += 1
        
        over_represented = [g for g, c in genre_count.items() if c > len(songs) // 3]
        
        new_songs = []
        replaced = 0
        
        for song in songs:
            if song.get("genre", "") in over_represented and replaced < 3:
                for rec in all_recommendations:
                    if (rec.get("genre", "") not in over_represented and 
                        rec.get("song_id") not in [s.get("song_id") for s in new_songs + songs]):
                        new_songs.append({
                            "song_id": rec.get("song_id", ""),
                            "title": rec.get("title", ""),
                            "artist": rec.get("artist", ""),
                            "genre": rec.get("genre", ""),
                            "year": rec.get("year", 2000),
                            "score": rec.get("score", 0.5),
                            "reason": "增加歌单多样性"
                        })
                        replaced += 1
                        break
                    else:
                        new_songs.append(song)
            else:
                new_songs.append(song)
        
        return new_songs
    
    def generate_smart_mix(self, 
                           user_recommendations: List[Dict],
                           similar_songs: List[Dict],
                           explore_songs: List[Dict],
                           playlist_size: int = 30) -> GeneratedPlaylist:
        theme = PlaylistTheme(
            theme_id="smart_mix",
            name="Smart Mix",
            description="智能混合歌单，融合您的喜好与新发现",
            keywords=["mix", "smart", "discover"],
            target_genres=[],
            mood="varied",
            energy_level="mixed"
        )
        
        num_favorites = int(playlist_size * 0.5)
        num_similar = int(playlist_size * 0.3)
        num_explore = playlist_size - num_favorites - num_similar
        
        selected = []
        
        favorite_recs = sorted(user_recommendations, key=lambda x: x.get("score", 0), reverse=True)
        for rec in favorite_recs[:num_favorites]:
            selected.append({
                **rec,
                "reason": "您的最爱"
            })
        
        similar_recs = sorted(similar_songs, key=lambda x: x.get("score", 0), reverse=True)
        for rec in similar_recs[:num_similar]:
            selected.append({
                **rec,
                "reason": "相似风格"
            })
        
        for rec in explore_songs[:num_explore]:
            selected.append({
                **rec,
                "reason": "新鲜发现"
            })
        
        random.shuffle(selected)
        
        diversity = self.calculate_diversity(selected)
        
        playlist_id = f"smart_{int(datetime.now().timestamp())}"
        
        return GeneratedPlaylist(
            playlist_id=playlist_id,
            name="Smart Mix - 智能推荐",
            description="融合您喜爱的歌曲、相似风格和新发现的智能歌单",
            theme="smart_mix",
            songs=[PlaylistItem(**{k: v for k, v in s.items() 
                                   if k in PlaylistItem.model_fields}) for s in selected],
            generated_at=datetime.now(),
            diversity_score=diversity,
            coherence_score=0.7
        )
    
    def get_all_themes(self) -> List[Dict]:
        return [
            {
                "theme_id": theme.theme_id,
                "name": theme.name,
                "description": theme.description,
                "target_genres": theme.target_genres,
                "mood": theme.mood,
                "energy_level": theme.energy_level
            }
            for theme in self.themes
        ]
