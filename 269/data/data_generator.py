import random
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from .models import Song, User, UserBehavior, Genre, ActionType


class DataGenerator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.songs: List[Song] = []
        self.users: List[User] = []
        self.behaviors: List[UserBehavior] = []
    
    def generate_songs(self, num_songs: int = 100) -> List[Song]:
        genres = list(Genre)
        artists = [
            "Taylor Swift", "Ed Sheeran", "Drake", "Adele", "Bruno Mars",
            "The Weeknd", "Billie Eilish", "Post Malone", "Ariana Grande", "Justin Bieber",
            "Dua Lipa", "Harry Styles", "Doja Cat", "Lizzo", "Lil Nas X",
            "Olivia Rodrigo", "BTS", "Bad Bunny", "The Weeknd", "Coldplay"
        ]
        titles = [
            "Midnight Dreams", "Summer Vibes", "Broken Heart", "Forever Young", "Electric Soul",
            "Rhythm of Love", "Starlight", "Ocean Waves", "City Lights", "Mountain High",
            "Rainy Days", "Sunshine Boulevard", "Moon River", "Autumn Leaves", "Winter Wonderland",
            "Spring Breeze", "Neon Nights", "Golden Hour", "Paradise", "Freedom"
        ]
        
        for i in range(num_songs):
            song = Song(
                song_id=f"s_{i+1:04d}",
                title=f"{random.choice(titles)} {i+1}",
                artist=random.choice(artists),
                genre=random.choice(genres),
                year=random.randint(1990, 2024),
                popularity=round(random.random(), 2)
            )
            self.songs.append(song)
        
        return self.songs
    
    def generate_users(self, num_users: int = 50) -> List[User]:
        genres = list(Genre)
        names = [
            "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
            "Ivy", "Jack", "Katie", "Leo", "Mia", "Noah", "Olivia", "Paul",
            "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander"
        ]
        
        for i in range(num_users):
            num_favorites = random.randint(1, 4)
            user = User(
                user_id=f"u_{i+1:04d}",
                name=random.choice(names) if i < len(names) else f"User_{i+1}",
                favorite_genres=random.sample(genres, num_favorites)
            )
            self.users.append(user)
        
        return self.users
    
    def generate_behaviors(self, min_behaviors_per_user: int = 10, 
                          max_behaviors_per_user: int = 50) -> List[UserBehavior]:
        song_ids = [song.song_id for song in self.songs]
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        for user in self.users:
            num_behaviors = random.randint(min_behaviors_per_user, max_behaviors_per_user)
            
            user_song_preferences = {}
            for song in self.songs:
                base_score = 1.0
                if song.genre in user.favorite_genres:
                    base_score *= 2.0
                base_score *= song.popularity
                user_song_preferences[song.song_id] = base_score
            
            weighted_songs = []
            weights = []
            for song_id, score in user_song_preferences.items():
                weighted_songs.append(song_id)
                weights.append(score)
            
            for _ in range(num_behaviors):
                song_id = random.choices(weighted_songs, weights=weights, k=1)[0]
                
                song = next(s for s in self.songs if s.song_id == song_id)
                like_prob = 0.7 if song.genre in user.favorite_genres else 0.3
                
                if random.random() < like_prob:
                    action = ActionType.PLAY
                    play_duration = random.uniform(60, 240)
                else:
                    action = ActionType.SKIP
                    play_duration = random.uniform(5, 30)
                
                if action == ActionType.PLAY and random.random() < 0.3:
                    self.behaviors.append(UserBehavior(
                        user_id=user.user_id,
                        song_id=song_id,
                        action=ActionType.LIKE,
                        timestamp=self._random_time(start_time, end_time),
                        play_duration=play_duration
                    ))
                
                self.behaviors.append(UserBehavior(
                    user_id=user.user_id,
                    song_id=song_id,
                    action=action,
                    timestamp=self._random_time(start_time, end_time),
                    play_duration=play_duration
                ))
        
        return self.behaviors
    
    def _random_time(self, start: datetime, end: datetime) -> datetime:
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)
    
    def get_ratings_dataframe(self) -> pd.DataFrame:
        ratings = []
        for behavior in self.behaviors:
            if behavior.action == ActionType.LIKE:
                rating = 5.0
            elif behavior.action == ActionType.PLAY:
                rating = 3.5 + (behavior.play_duration or 120) / 240 * 1.5
            else:
                rating = 1.0
            
            ratings.append({
                "user_id": behavior.user_id,
                "song_id": behavior.song_id,
                "rating": round(rating, 2)
            })
        
        df = pd.DataFrame(ratings)
        df = df.groupby(["user_id", "song_id"], as_index=False)["rating"].mean()
        return df
    
    def get_songs_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([song.model_dump() for song in self.songs])
    
    def save_all(self, output_dir: str = "./data"):
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        songs_df = self.get_songs_dataframe()
        ratings_df = self.get_ratings_dataframe()
        
        songs_df.to_csv(f"{output_dir}/songs.csv", index=False)
        ratings_df.to_csv(f"{output_dir}/ratings.csv", index=False)
        
        print(f"Generated {len(self.songs)} songs, {len(self.users)} users, {len(self.behaviors)} behaviors")
        print(f"Saved to {output_dir}/")
    
    @staticmethod
    def load_songs_from_csv(filepath: str) -> List[Song]:
        df = pd.read_csv(filepath)
        return [Song(**row) for _, row in df.iterrows()]
