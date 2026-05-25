import os
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from config import settings


class ImageFeatureExtractor:
    def __init__(self, feature_dim: int = 128):
        self.feature_dim = feature_dim
        self._mock_color_palettes = [
            "warm", "cool", "dark", "bright", "pastel", "neon", "vintage", "minimalist"
        ]
        self._mock_genres = [
            "rock", "pop", "jazz", "electronic", "classical", "hiphop", "country", "rnb"
        ]
    
    def extract_features(self, song_id: str, genre: str = None) -> np.ndarray:
        np.random.seed(hash(song_id) % 4294967295)
        
        features = np.random.randn(self.feature_dim)
        
        if genre and genre in self._mock_genres:
            genre_idx = self._mock_genres.index(genre)
            features[genre_idx % self.feature_dim] += 0.5
            features[(genre_idx + 4) % self.feature_dim] += 0.3
        
        palette_idx = hash(song_id) % len(self._mock_color_palettes)
        features[(palette_idx + 8) % self.feature_dim] += 0.4
        
        return normalize(features.reshape(1, -1)).flatten()
    
    def batch_extract(self, songs: List[Dict]) -> Dict[str, np.ndarray]:
        features = {}
        for song in songs:
            song_id = song.get("song_id", song.get("id"))
            genre = song.get("genre", None)
            features[song_id] = self.extract_features(song_id, genre)
        return features


class LyricTextFeatureExtractor:
    def __init__(self, max_features: int = 500):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            stop_words="english"
        )
        self._mock_lyrics_themes = {
            "love": ["love", "heart", "romance", "kiss", "forever", "together", "baby", "sweet"],
            "sad": ["cry", "pain", "broken", "lonely", "goodbye", "miss", "sad", "blue"],
            "party": ["dance", "party", "night", "club", "music", "beat", "shake", "fun"],
            "hope": ["dream", "hope", "light", "believe", "fly", "free", "rise", "strong"],
            "life": ["life", "time", "world", "people", "way", "home", "day", "eyes"],
            "rock": ["rock", "roll", "guitar", "loud", "wild", "fire", "burn", "night"],
            "hiphop": ["rap", "flow", "street", "money", "real", "game", "gang", "mic"],
            "electronic": ["beat", "drop", "bass", "electric", "pulse", "wave", "techno", "dance"]
        }
        self._fitted = False
    
    def _generate_mock_lyrics(self, song_id: str, genre: str = None) -> str:
        np.random.seed(hash(song_id) % 4294967295)
        
        themes = list(self._mock_lyrics_themes.keys())
        num_themes = np.random.randint(2, 5)
        selected_themes = np.random.choice(themes, num_themes, replace=False)
        
        if genre and genre in self._mock_lyrics_themes:
            selected_themes = np.append(selected_themes, genre)
        
        lyrics_words = []
        for theme in selected_themes:
            theme_words = self._mock_lyrics_themes[theme]
            num_words = np.random.randint(3, 8)
            lyrics_words.extend(np.random.choice(theme_words, num_words))
        
        np.random.shuffle(lyrics_words)
        return " ".join(lyrics_words)
    
    def fit(self, songs: List[Dict]):
        lyrics_corpus = []
        for song in songs:
            song_id = song.get("song_id", song.get("id"))
            genre = song.get("genre", None)
            lyrics = self._generate_mock_lyrics(song_id, genre)
            lyrics_corpus.append(lyrics)
        
        self.vectorizer.fit(lyrics_corpus)
        self._fitted = True
        return self
    
    def extract_features(self, song_id: str, genre: str = None) -> np.ndarray:
        if not self._fitted:
            raise ValueError("Vectorizer not fitted. Call fit() first.")
        
        lyrics = self._generate_mock_lyrics(song_id, genre)
        features = self.vectorizer.transform([lyrics])
        return features.toarray().flatten()
    
    def batch_extract(self, songs: List[Dict]) -> Dict[str, np.ndarray]:
        if not self._fitted:
            self.fit(songs)
        
        features = {}
        for song in songs:
            song_id = song.get("song_id", song.get("id"))
            genre = song.get("genre", None)
            features[song_id] = self.extract_features(song_id, genre)
        return features


class MultimodalSimilarity:
    def __init__(self, 
                 image_weight: float = 0.3,
                 text_weight: float = 0.3,
                 content_weight: float = 0.4):
        self.image_weight = image_weight
        self.text_weight = text_weight
        self.content_weight = content_weight
        
        self.image_extractor = ImageFeatureExtractor()
        self.text_extractor = LyricTextFeatureExtractor()
        
        self.image_features: Dict[str, np.ndarray] = {}
        self.text_features: Dict[str, np.ndarray] = {}
        self.similarity_matrix: Optional[np.ndarray] = None
        self.song_id_to_idx: Dict[str, int] = {}
        self.idx_to_song_id: Dict[int, str] = {}
    
    def build_multimodal_features(self, songs_df: pd.DataFrame):
        songs_list = songs_df.to_dict("records")
        
        print("Extracting image features...")
        self.image_features = self.image_extractor.batch_extract(songs_list)
        
        print("Extracting text/lyrics features...")
        self.text_features = self.text_extractor.batch_extract(songs_list)
        
        self.song_id_to_idx = {row["song_id"]: idx for idx, row in songs_df.iterrows()}
        self.idx_to_song_id = {idx: song_id for song_id, idx in self.song_id_to_idx.items()}
        
        print("Building multimodal similarity matrix...")
        num_songs = len(songs_df)
        
        image_sim = np.zeros((num_songs, num_songs))
        text_sim = np.zeros((num_songs, num_songs))
        
        for i, song_id_i in self.idx_to_song_id.items():
            for j, song_id_j in self.idx_to_song_id.items():
                if i <= j:
                    img_feat_i = self.image_features[song_id_i].reshape(1, -1)
                    img_feat_j = self.image_features[song_id_j].reshape(1, -1)
                    image_sim[i, j] = cosine_similarity(img_feat_i, img_feat_j)[0, 0]
                    image_sim[j, i] = image_sim[i, j]
                    
                    text_feat_i = self.text_features[song_id_i].reshape(1, -1)
                    text_feat_j = self.text_features[song_id_j].reshape(1, -1)
                    text_sim[i, j] = cosine_similarity(text_feat_i, text_feat_j)[0, 0]
                    text_sim[j, i] = text_sim[i, j]
        
        self.similarity_matrix = (
            self.image_weight * image_sim +
            self.text_weight * text_sim
        )
        
        print(f"Multimodal similarity matrix built: {num_songs} songs")
        return self.similarity_matrix
    
    def combine_with_content_similarity(self, content_sim_matrix: np.ndarray):
        if self.similarity_matrix is None:
            self.similarity_matrix = content_sim_matrix
            return self.similarity_matrix
        
        self.similarity_matrix = (
            (1 - self.content_weight) * self.similarity_matrix +
            self.content_weight * content_sim_matrix
        )
        return self.similarity_matrix
    
    def get_similar_songs(self, song_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        if self.similarity_matrix is None:
            raise ValueError("Similarity matrix not built. Call build_multimodal_features() first.")
        
        if song_id not in self.song_id_to_idx:
            return []
        
        song_idx = self.song_id_to_idx[song_id]
        similarity_scores = self.similarity_matrix[song_idx]
        
        similar_indices = similarity_scores.argsort()[::-1][1:top_n + 1]
        similar_songs = []
        for idx in similar_indices:
            sim_song_id = self.idx_to_song_id[idx]
            score = round(similarity_scores[idx], 4)
            similar_songs.append((sim_song_id, score))
        
        return similar_songs
    
    def get_multimodal_reason(self, song_id: str, 
                            user_liked_songs: List[str]) -> List[str]:
        reasons = []
        
        if song_id not in self.image_features:
            return reasons
        
        max_img_sim = 0
        max_text_sim = 0
        
        for liked_id in user_liked_songs:
            if liked_id in self.image_features and liked_id in self.text_features:
                img_feat1 = self.image_features[song_id].reshape(1, -1)
                img_feat2 = self.image_features[liked_id].reshape(1, -1)
                img_sim = cosine_similarity(img_feat1, img_feat2)[0, 0]
                max_img_sim = max(max_img_sim, img_sim)
                
                text_feat1 = self.text_features[song_id].reshape(1, -1)
                text_feat2 = self.text_features[liked_id].reshape(1, -1)
                text_sim = cosine_similarity(text_feat1, text_feat2)[0, 0]
                max_text_sim = max(max_text_sim, text_sim)
        
        if max_img_sim > 0.7:
            visual_reasons = [
                "专辑封面视觉风格匹配",
                "视觉元素相似",
                "封面艺术风格相近"
            ]
            reasons.append(np.random.choice(visual_reasons))
        
        if max_text_sim > 0.5:
            lyric_reasons = [
                "歌词主题相似",
                "歌曲意境相近",
                "歌词情感共鸣"
            ]
            reasons.append(np.random.choice(lyric_reasons))
        
        return reasons
    
    def save(self, path: str = "./models/multimodal.pkl"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        save_data = {
            "image_weight": self.image_weight,
            "text_weight": self.text_weight,
            "content_weight": self.content_weight,
            "image_features": self.image_features,
            "text_features": self.text_features,
            "similarity_matrix": self.similarity_matrix,
            "song_id_to_idx": self.song_id_to_idx,
            "idx_to_song_id": self.idx_to_song_id,
            "text_vectorizer": self.text_extractor.vectorizer
        }
        
        with open(path, "wb") as f:
            pickle.dump(save_data, f)
    
    def load(self, path: str = "./models/multimodal.pkl"):
        with open(path, "rb") as f:
            save_data = pickle.load(f)
        
        self.image_weight = save_data["image_weight"]
        self.text_weight = save_data["text_weight"]
        self.content_weight = save_data["content_weight"]
        self.image_features = save_data["image_features"]
        self.text_features = save_data["text_features"]
        self.similarity_matrix = save_data["similarity_matrix"]
        self.song_id_to_idx = save_data["song_id_to_idx"]
        self.idx_to_song_id = save_data["idx_to_song_id"]
        self.text_extractor.vectorizer = save_data["text_vectorizer"]
        self.text_extractor._fitted = True
