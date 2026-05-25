import os
import pickle
import pandas as pd
from typing import List, Dict, Tuple
from surprise import Dataset, Reader, SVD, KNNBaseline
from surprise.model_selection import train_test_split
from surprise import accuracy
from config import settings


class CollaborativeFilteringRecommender:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or settings.CF_MODEL_PATH
        self.model = None
        self.trainset = None
        self.user_id_map = {}
        self.song_id_map = {}
        self.reverse_user_id_map = {}
        self.reverse_song_id_map = {}
    
    def _prepare_data(self, ratings_df: pd.DataFrame) -> Dataset:
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(
            ratings_df[["user_id", "song_id", "rating"]],
            reader
        )
        return data
    
    def _build_id_maps(self, ratings_df: pd.DataFrame):
        unique_users = ratings_df["user_id"].unique()
        unique_songs = ratings_df["song_id"].unique()
        
        self.user_id_map = {uid: idx for idx, uid in enumerate(unique_users)}
        self.song_id_map = {sid: idx for idx, sid in enumerate(unique_songs)}
        self.reverse_user_id_map = {idx: uid for uid, idx in self.user_id_map.items()}
        self.reverse_song_id_map = {idx: sid for sid, idx in self.song_id_map.items()}
    
    def train(self, ratings_df: pd.DataFrame, method: str = "svd") -> Dict[str, float]:
        self._build_id_maps(ratings_df)
        data = self._prepare_data(ratings_df)
        trainset, testset = train_test_split(data, test_size=0.2, random_state=42)
        self.trainset = trainset
        
        if method == "svd":
            self.model = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
        elif method == "knn":
            sim_options = {
                "name": "cosine",
                "user_based": False
            }
            self.model = KNNBaseline(sim_options=sim_options)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        self.model.fit(trainset)
        predictions = self.model.test(testset)
        rmse = accuracy.rmse(predictions, verbose=False)
        mae = accuracy.mae(predictions, verbose=False)
        
        return {"rmse": round(rmse, 4), "mae": round(mae, 4)}
    
    def predict(self, user_id: str, song_id: str) -> float:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        try:
            prediction = self.model.predict(user_id, song_id)
            return prediction.est
        except:
            return 2.5
    
    def recommend_for_user(self, user_id: str, song_ids: List[str], 
                          top_n: int = 10) -> List[Tuple[str, float]]:
        predictions = []
        for song_id in song_ids:
            score = self.predict(user_id, song_id)
            predictions.append((song_id, score))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:top_n]
    
    def get_user_similar_users(self, user_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        if not hasattr(self.model, 'sim'):
            raise ValueError("KNN model required for similarity queries. Use method='knn' when training.")
        
        try:
            user_inner_id = self.trainset.to_inner_uid(user_id)
            neighbors = self.model.get_neighbors(user_inner_id, k=top_n)
            similar_users = []
            for neighbor_inner_id in neighbors:
                neighbor_id = self.trainset.to_raw_uid(neighbor_inner_id)
                sim_score = self.model.sim[user_inner_id, neighbor_inner_id]
                similar_users.append((neighbor_id, round(sim_score, 4)))
            return similar_users
        except:
            return []
    
    def get_song_similar_songs(self, song_id: str, top_n: int = 10) -> List[Tuple[str, float]]:
        if not hasattr(self.model, 'sim'):
            raise ValueError("KNN model required for similarity queries. Use method='knn' when training.")
        
        try:
            song_inner_id = self.trainset.to_inner_iid(song_id)
            neighbors = self.model.get_neighbors(song_inner_id, k=top_n)
            similar_songs = []
            for neighbor_inner_id in neighbors:
                neighbor_id = self.trainset.to_raw_iid(neighbor_inner_id)
                sim_score = self.model.sim[song_inner_id, neighbor_inner_id]
                similar_songs.append((neighbor_id, round(sim_score, 4)))
            return similar_songs
        except:
            return []
    
    def save(self, path: str = None):
        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        save_data = {
            "model": self.model,
            "trainset": self.trainset,
            "user_id_map": self.user_id_map,
            "song_id_map": self.song_id_map,
            "reverse_user_id_map": self.reverse_user_id_map,
            "reverse_song_id_map": self.reverse_song_id_map
        }
        
        with open(save_path, "wb") as f:
            pickle.dump(save_data, f)
    
    def load(self, path: str = None):
        load_path = path or self.model_path
        
        with open(load_path, "rb") as f:
            save_data = pickle.load(f)
        
        self.model = save_data["model"]
        self.trainset = save_data["trainset"]
        self.user_id_map = save_data["user_id_map"]
        self.song_id_map = save_data["song_id_map"]
        self.reverse_user_id_map = save_data["reverse_user_id_map"]
        self.reverse_song_id_map = save_data["reverse_song_id_map"]
