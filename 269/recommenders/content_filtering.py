import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from config import settings


class ContentFilteringRecommender:
    def __init__(self, similarity_matrix_path: str = None):
        self.similarity_matrix_path = similarity_matrix_path or settings.SIMILARITY_MATRIX_PATH
        self.songs_df = None
        self.similarity_matrix = None
        self.song_id_to_idx = {}
        self.idx_to_song_id = {}
        self.encoder = None
        self.scaler = None
        self.feature_matrix = None
    
    def build_feature_matrix(self, songs_df: pd.DataFrame):
        self.songs_df = songs_df.reset_index(drop=True)
        self.song_id_to_idx = {row["song_id"]: idx for idx, row in self.songs_df.iterrows()}
        self.idx_to_song_id = {idx: song_id for song_id, idx in self.song_id_to_idx.items()}
        
        genre_encoder = OneHotEncoder(sparse_output=False)
        genre_features = genre_encoder.fit_transform(self.songs_df[["genre"]])
        
        artist_vectorizer = TfidfVectorizer()
        artist_features = artist_vectorizer.fit_transform(self.songs_df["artist"]).toarray()
        
        scaler = StandardScaler()
        year_features = scaler.fit_transform(self.songs_df[["year"]])
        
        popularity_features = self.songs_df[["popularity"]].values
        
        self.feature_matrix = np.hstack([
            genre_features,
            artist_features,
            year_features,
            popularity_features
        ])
        
        self.encoder = genre_encoder
        self.scaler = scaler
    
    def compute_similarity_matrix(self):
        if self.feature_matrix is None:
            raise ValueError("Feature matrix not built. Call build_feature_matrix() first.")
        
        self.similarity_matrix = cosine_similarity(self.feature_matrix)
        return self.similarity_matrix
    
    def get_song_similar_songs(self, song_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not computed. Call compute_similarity_matrix() first.")
        
        if song_id not in self.song_id_to_idx:
            return []
        
        song_idx = self.song_id_to_idx[song_id]
        similarity_scores = self.similarity_matrix[song_idx]
        
        similar_indices = similarity_scores.argsort()[::-1][1:top_n+1]
        similar_songs = []
        for idx in similar_indices:
            similar_song_id = self.idx_to_song_id[idx]
            score = round(similarity_scores[idx], 4)
            similar_songs.append((similar_song_id, score))
        
        return similar_songs
    
    def recommend_for_user(self, user_liked_songs: List[str], 
                          all_song_ids: List[str],
                          top_n: int = 10) -> List[Tuple[str, float]]:
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not computed. Call compute_similarity_matrix() first.")
        
        liked_indices = []
        for song_id in user_liked_songs:
            if song_id in self.song_id_to_idx:
                liked_indices.append(self.song_id_to_idx[song_id])
        
        if not liked_indices:
            return []
        
        scores = np.zeros(len(self.songs_df))
        for idx in liked_indices:
            scores += self.similarity_matrix[idx]
        
        scores /= len(liked_indices)
        
        candidate_songs = []
        for song_id in all_song_ids:
            if song_id not in user_liked_songs and song_id in self.song_id_to_idx:
                song_idx = self.song_id_to_idx[song_id]
                candidate_songs.append((song_id, round(scores[song_idx], 4)))
        
        candidate_songs.sort(key=lambda x: x[1], reverse=True)
        return candidate_songs[:top_n]
    
    def get_recommendation_reason(self, song_id: str, user_liked_songs: List[str]) -> str:
        if song_id not in self.song_id_to_idx:
            return "基于您的听歌历史推荐"
        
        song = self.songs_df[self.songs_df["song_id"] == song_id].iloc[0]
        reasons = []
        
        liked_same_artist = []
        liked_same_genre = []
        liked_similar_year = []
        
        for liked_id in user_liked_songs:
            if liked_id in self.song_id_to_idx:
                liked_song = self.songs_df[self.songs_df["song_id"] == liked_id].iloc[0]
                if liked_song["artist"] == song["artist"]:
                    liked_same_artist.append(liked_song["title"])
                if liked_song["genre"] == song["genre"]:
                    liked_same_genre.append(liked_song["title"])
                if abs(liked_song["year"] - song["year"]) <= 5:
                    liked_similar_year.append(liked_song["title"])
        
        if liked_same_artist:
            reasons.append(f"与您喜欢的{song['artist']}的其他歌曲风格相似")
        if liked_same_genre:
            reasons.append(f"属于您喜欢的{song['genre']}风格")
        if liked_similar_year and not reasons:
            reasons.append(f"与您喜欢的{song['year']}年代的歌曲风格相似")
        
        if not reasons:
            reasons.append("基于歌曲内容相似度推荐")
        
        return "；".join(reasons)
    
    def save(self, path: str = None):
        save_path = path or self.similarity_matrix_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        save_data = {
            "songs_df": self.songs_df,
            "similarity_matrix": self.similarity_matrix,
            "song_id_to_idx": self.song_id_to_idx,
            "idx_to_song_id": self.idx_to_song_id,
            "encoder": self.encoder,
            "scaler": self.scaler,
            "feature_matrix": self.feature_matrix
        }
        
        with open(save_path, "wb") as f:
            pickle.dump(save_data, f)
    
    def load(self, path: str = None):
        load_path = path or self.similarity_matrix_path
        
        with open(load_path, "rb") as f:
            save_data = pickle.load(f)
        
        self.songs_df = save_data["songs_df"]
        self.similarity_matrix = save_data["similarity_matrix"]
        self.song_id_to_idx = save_data["song_id_to_idx"]
        self.idx_to_song_id = save_data["idx_to_song_id"]
        self.encoder = save_data["encoder"]
        self.scaler = save_data["scaler"]
        self.feature_matrix = save_data["feature_matrix"]
