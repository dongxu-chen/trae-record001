import os
import json
import librosa
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MusicTrack:
    id: str
    name: str
    artist: str
    genre: str
    mood: str
    bpm: int
    duration: float
    energy: float
    danceability: float
    valence: float
    file_path: str
    preview_url: Optional[str] = None


@dataclass
class VideoRhythm:
    bpm: float
    energy_profile: List[float]
    scene_change_rate: float
    avg_motion_intensity: float
    dominant_mood: str


class MusicRecommender:
    def __init__(self, music_library_path: Optional[str] = None):
        self.music_library: List[MusicTrack] = []
        self.library_path = music_library_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'music_library'
        )
        self._load_default_library()

    def _load_default_library(self):
        default_tracks = [
            {
                'id': 'epic_001',
                'name': 'Rise to Glory',
                'artist': 'Cinematic Sounds',
                'genre': 'Epic',
                'mood': 'epic',
                'bpm': 140,
                'duration': 180.0,
                'energy': 0.9,
                'danceability': 0.4,
                'valence': 0.8,
                'file_path': ''
            },
            {
                'id': 'upbeat_001',
                'name': 'Summer Vibes',
                'artist': 'Happy Beats',
                'genre': 'Pop',
                'mood': 'happy',
                'bpm': 120,
                'duration': 165.0,
                'energy': 0.75,
                'danceability': 0.8,
                'valence': 0.9,
                'file_path': ''
            },
            {
                'id': 'relaxed_001',
                'name': 'Morning Calm',
                'artist': 'Ambient Dreams',
                'genre': 'Ambient',
                'mood': 'calm',
                'bpm': 70,
                'duration': 240.0,
                'energy': 0.2,
                'danceability': 0.2,
                'valence': 0.6,
                'file_path': ''
            },
            {
                'id': 'action_001',
                'name': 'Pursuit',
                'artist': 'Action Trailers',
                'genre': 'Action',
                'mood': 'intense',
                'bpm': 160,
                'duration': 120.0,
                'energy': 0.95,
                'danceability': 0.5,
                'valence': 0.3,
                'file_path': ''
            },
            {
                'id': 'romantic_001',
                'name': 'Forever Yours',
                'artist': 'Love Stories',
                'genre': 'Romantic',
                'mood': 'romantic',
                'bpm': 90,
                'duration': 200.0,
                'energy': 0.4,
                'danceability': 0.5,
                'valence': 0.95,
                'file_path': ''
            },
            {
                'id': 'electronic_001',
                'name': 'Neon Nights',
                'artist': 'Synthwave',
                'genre': 'Electronic',
                'mood': 'energetic',
                'bpm': 128,
                'duration': 210.0,
                'energy': 0.85,
                'danceability': 0.9,
                'valence': 0.7,
                'file_path': ''
            },
            {
                'id': 'sad_001',
                'name': 'Fading Memories',
                'artist': 'Emotional Piano',
                'genre': 'Piano',
                'mood': 'sad',
                'bpm': 65,
                'duration': 180.0,
                'energy': 0.15,
                'danceability': 0.1,
                'valence': 0.1,
                'file_path': ''
            },
            {
                'id': 'adventure_001',
                'name': 'Explore the World',
                'artist': 'World Beats',
                'genre': 'World',
                'mood': 'adventurous',
                'bpm': 110,
                'duration': 190.0,
                'energy': 0.7,
                'danceability': 0.6,
                'valence': 0.85,
                'file_path': ''
            }
        ]
        
        for track_data in default_tracks:
            self.music_library.append(MusicTrack(**track_data))

    def analyze_video_rhythm(
        self,
        video_path: str,
        highlights: List[Dict],
        scenes: List[Dict],
        motion_profile: Optional[List[float]] = None
    ) -> VideoRhythm:
        if motion_profile is None:
            motion_profile = [h.get('intensity', 0.5) for h in highlights] if highlights else [0.5]

        avg_motion = np.mean(motion_profile) if motion_profile else 0.5

        bpm_estimate = self._estimate_bpm_from_scenes(scenes, highlights)
        
        scene_change_rate = len(scenes) / max(1, scenes[-1].get('end_time', 60) if scenes else 60)

        mood = self._detect_mood(highlights, avg_motion, scene_change_rate)

        return VideoRhythm(
            bpm=bpm_estimate,
            energy_profile=motion_profile,
            scene_change_rate=scene_change_rate,
            avg_motion_intensity=avg_motion,
            dominant_mood=mood
        )

    def _estimate_bpm_from_scenes(self, scenes: List[Dict], highlights: List[Dict]) -> float:
        if not highlights:
            return 100.0
        
        highlight_density = len(highlights) / max(1, max(h.get('end_time', 0) for h in highlights))
        
        bpm_range = {
            'very_low': (60, 80),
            'low': (80, 100),
            'medium': (100, 120),
            'high': (120, 140),
            'very_high': (140, 170)
        }
        
        if highlight_density < 0.05:
            bpm_min, bpm_max = bpm_range['very_low']
        elif highlight_density < 0.1:
            bpm_min, bpm_max = bpm_range['low']
        elif highlight_density < 0.2:
            bpm_min, bpm_max = bpm_range['medium']
        elif highlight_density < 0.35:
            bpm_min, bpm_max = bpm_range['high']
        else:
            bpm_min, bpm_max = bpm_range['very_high']
        
        return (bpm_min + bpm_max) / 2

    def _detect_mood(self, highlights: List[Dict], avg_motion: float, scene_rate: float) -> str:
        highlight_types = [h.get('type', 'motion') for h in highlights]
        
        motion_count = highlight_types.count('motion')
        brightness_count = highlight_types.count('brightness')
        audio_count = highlight_types.count('audio_peak') + highlight_types.count('laughter')
        
        total = max(1, len(highlight_types))
        motion_ratio = motion_count / total
        audio_ratio = audio_count / total
        
        if avg_motion > 0.7 and scene_rate > 0.5:
            if motion_ratio > 0.5:
                return 'intense'
            return 'energetic'
        elif avg_motion > 0.5:
            if audio_ratio > 0.3:
                return 'happy'
            return 'adventurous'
        elif avg_motion < 0.25:
            return 'calm'
        elif brightness_count > total * 0.3:
            return 'romantic'
        elif motion_ratio < 0.2:
            return 'sad'
        
        return 'epic'

    def recommend_music(
        self,
        video_rhythm: VideoRhythm,
        target_duration: Optional[float] = None,
        genre_filter: Optional[List[str]] = None,
        mood_filter: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Tuple[MusicTrack, float]]:
        candidates = self.music_library.copy()
        
        if genre_filter:
            candidates = [t for t in candidates if t.genre in genre_filter]
        
        if mood_filter:
            candidates = [t for t in candidates if t.mood in mood_filter]
        
        if target_duration:
            candidates = [t for t in candidates if t.duration >= target_duration * 0.8]
        
        scored = []
        for track in candidates:
            score = self._calculate_match_score(track, video_rhythm)
            scored.append((track, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _calculate_match_score(self, track: MusicTrack, rhythm: VideoRhythm) -> float:
        score = 0.0
        
        bpm_diff = abs(track.bpm - rhythm.bpm)
        bpm_score = max(0, 1 - bpm_diff / 80) * 0.3
        score += bpm_score
        
        energy_diff = abs(track.energy - rhythm.avg_motion_intensity)
        energy_score = max(0, 1 - energy_diff) * 0.25
        score += energy_score
        
        mood_match = self._mood_similarity(track.mood, rhythm.dominant_mood)
        mood_score = mood_match * 0.35
        score += mood_score
        
        scene_penalty = min(1, rhythm.scene_change_rate / 2)
        danceability_score = track.danceability * scene_penalty * 0.1
        score += danceability_score
        
        return score

    def _mood_similarity(self, mood1: str, mood2: str) -> float:
        mood_groups = {
            'energetic': {'energetic', 'intense', 'epic', 'adventurous'},
            'positive': {'happy', 'epic', 'adventurous', 'romantic'},
            'calm': {'calm', 'romantic', 'sad'},
            'intense': {'intense', 'epic'}
        }
        
        if mood1 == mood2:
            return 1.0
        
        for group, moods in mood_groups.items():
            if mood1 in moods and mood2 in moods:
                return 0.7
        
        return 0.3

    def get_all_tracks(self) -> List[MusicTrack]:
        return self.music_library

    def get_genres(self) -> List[str]:
        return list({t.genre for t in self.music_library})

    def get_moods(self) -> List[str]:
        return list({t.mood for t in self.music_library})
