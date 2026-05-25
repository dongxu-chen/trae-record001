import numpy as np
from typing import List, Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from config import settings


class ActionWeights:
    LIKE = 2.0
    PLAY_COMPLETE = 1.0
    PLAY_PARTIAL = 0.3
    SKIP = -1.0
    DISLIKE = -2.0


class RealTimeFeedbackUpdater:
    def __init__(self, decay_rate: float = 0.05, max_history: int = 1000):
        self.decay_rate = decay_rate
        self.max_history = max_history
        
        self.user_action_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        
        self.user_song_weights: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        self.user_preference_vector: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        
        self.user_skip_patterns: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        
        self.user_genre_skip_rate: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def record_action(self, user_id: str, song_id: str, action: str, 
                      timestamp: datetime = None, **kwargs):
        if timestamp is None:
            timestamp = datetime.now()
        
        action_data = {
            "song_id": song_id,
            "action": action,
            "timestamp": timestamp,
            **kwargs
        }
        
        self.user_action_history[user_id].append(action_data)
        self._update_weights(user_id, song_id, action, **kwargs)
        self._update_preferences(user_id, song_id, action, **kwargs)
        
        if action == "skip":
            self._update_skip_patterns(user_id, song_id, **kwargs)
    
    def _update_weights(self, user_id: str, song_id: str, action: str, **kwargs):
        weight = self._get_action_weight(action, **kwargs)
        current_weight = self.user_song_weights[user_id].get(song_id, 0)
        
        self.user_song_weights[user_id][song_id] = current_weight + weight
    
    def _get_action_weight(self, action: str, **kwargs) -> float:
        action_weights = {
            "like": ActionWeights.LIKE,
            "play_complete": ActionWeights.PLAY_COMPLETE,
            "play_partial": ActionWeights.PLAY_PARTIAL,
            "skip": ActionWeights.SKIP,
            "dislike": ActionWeights.DISLIKE
        }
        
        return action_weights.get(action, 0)
    
    def _update_preferences(self, user_id: str, song_id: str, action: str, **kwargs):
        song_info = kwargs.get("song_info", {})
        weight = self._get_action_weight(action, **kwargs)
        
        genre = song_info.get("genre")
        if genre:
            self.user_preference_vector[user_id][genre] += weight
        
        artist = song_info.get("artist")
        if artist:
            self.user_preference_vector[user_id][f"artist:{artist}"] += weight * 0.5
        
        year = song_info.get("year")
        if year:
            decade = f"decade:{(year // 10) * 10}"
            self.user_preference_vector[user_id][decade] += weight * 0.3
    
    def _update_skip_patterns(self, user_id: str, song_id: str, **kwargs):
        song_info = kwargs.get("song_info", {})
        
        genre = song_info.get("genre")
        if genre:
            self.user_skip_patterns[user_id][genre] += 1
    
    def calculate_adjusted_scores(self, user_id: str, 
                                   base_scores: Dict[str, float],
                                   songs_map: Dict) -> Dict[str, float]:
        adjusted_scores = {}
        
        for song_id, base_score in base_scores.items():
            song = songs_map.get(song_id)
            if not song:
                adjusted_scores[song_id] = base_score
                continue
            
            adjustment = self._calculate_adjustment(user_id, song)
            adjusted_score = base_score * (1 + adjustment)
            adjusted_scores[song_id] = max(0, min(1, adjusted_score))
        
        return adjusted_scores
    
    def _calculate_adjustment(self, user_id: str, song) -> float:
        adjustment = 0.0
        
        song_id = song.song_id
        explicit_weight = self.user_song_weights[user_id].get(song_id, 0)
        adjustment += explicit_weight * 0.1
        
        genre = getattr(song, "genre", None)
        if genre:
            genre_pref = self.user_preference_vector[user_id].get(genre, 0)
            adjustment += np.tanh(genre_pref * 0.1) * 0.2
            
            skip_count = self.user_skip_patterns[user_id].get(genre, 0)
            if skip_count > 3:
                adjustment -= 0.15
        
        artist = getattr(song, "artist", None)
        if artist:
            artist_pref = self.user_preference_vector[user_id].get(f"artist:{artist}", 0)
            adjustment += np.tanh(artist_pref * 0.1) * 0.15
        
        return adjustment
    
    def get_user_skip_statistics(self, user_id: str) -> Dict:
        skip_count = sum(1 for action in self.user_action_history[user_id] 
                        if action["action"] == "skip")
        total_count = len(self.user_action_history[user_id])
        
        skip_rate = skip_count / total_count if total_count > 0 else 0
        
        return {
            "total_actions": total_count,
            "skip_count": skip_count,
            "skip_rate": round(skip_rate, 4),
            "top_skipped_genres": dict(sorted(
                self.user_skip_patterns[user_id].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5])
        }
    
    def apply_time_decay(self, user_id: str, current_time: datetime = None):
        if current_time is None:
            current_time = datetime.now()
        
        for pref_key in list(self.user_preference_vector[user_id].keys()):
            self.user_preference_vector[user_id][pref_key] *= (1 - self.decay_rate)
            
            if abs(self.user_preference_vector[user_id][pref_key]) < 0.01:
                del self.user_preference_vector[user_id][pref_key]
    
    def get_user_preference_summary(self, user_id: str) -> Dict:
        prefs = self.user_preference_vector[user_id]
        
        genre_prefs = {k: v for k, v in prefs.items() 
                       if not k.startswith("artist:") and not k.startswith("decade:")}
        artist_prefs = {k.replace("artist:", ""): v for k, v in prefs.items() 
                        if k.startswith("artist:")}
        decade_prefs = {k.replace("decade:", ""): v for k, v in prefs.items() 
                        if k.startswith("decade:")}
        
        return {
            "top_genres": dict(sorted(genre_prefs.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_artists": dict(sorted(artist_prefs.items(), key=lambda x: x[1], reverse=True)[:5]),
            "top_decades": dict(sorted(decade_prefs.items(), key=lambda x: x[1], reverse=True)[:3])
        }


class SkipPenaltyManager:
    def __init__(self, base_penalty: float = 0.2, 
                 max_penalty: float = 0.5,
                 recovery_rate: float = 0.02):
        self.base_penalty = base_penalty
        self.max_penalty = max_penalty
        self.recovery_rate = recovery_rate
        
        self.user_genre_penalty: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.user_genre_play_count: Dict[str, Dict[str, int]] = defaultdict(dict)
    
    def record_skip(self, user_id: str, genre: str):
        current_penalty = self.user_genre_penalty[user_id].get(genre, 0)
        new_penalty = min(current_penalty + self.base_penalty, self.max_penalty)
        self.user_genre_penalty[user_id][genre] = new_penalty
    
    def record_play(self, user_id: str, genre: str):
        self.user_genre_play_count[user_id][genre] = \
            self.user_genre_play_count[user_id].get(genre, 0) + 1
        
        current_penalty = self.user_genre_penalty[user_id].get(genre, 0)
        if current_penalty > 0:
            self.user_genre_penalty[user_id][genre] = \
                max(0, current_penalty - self.recovery_rate)
    
    def get_penalty(self, user_id: str, genre: str) -> float:
        return self.user_genre_penalty[user_id].get(genre, 0)
    
    def apply_penalties(self, user_id: str, 
                         candidate_songs: List[Dict]) -> List[Dict]:
        adjusted = []
        for song in candidate_songs:
            genre = song.get("genre", "")
            penalty = self.get_penalty(user_id, genre)
            original_score = song.get("score", 0.5)
            adjusted_score = original_score * (1 - penalty)
            
            adjusted.append({
                **song,
                "original_score": original_score,
                "penalty": penalty,
                "adjusted_score": adjusted_score
            })
        
        return sorted(adjusted, key=lambda x: x["adjusted_score"], reverse=True)
