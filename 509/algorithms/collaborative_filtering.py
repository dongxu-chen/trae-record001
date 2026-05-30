import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from models.schemas import User, Dish, Order
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict


class CollaborativeFiltering:
    def __init__(self, users: Dict[str, User], dishes: Dict[str, Dish], orders: List[Order]):
        self.users = users
        self.dishes = dishes
        self.orders = orders
        self.user_ids = list(users.keys())
        self.dish_ids = list(dishes.keys())
        self.user_to_idx = {uid: i for i, uid in enumerate(self.user_ids)}
        self.dish_to_idx = {did: i for i, did in enumerate(self.dish_ids)}
        
        self.user_item_matrix = self._build_user_item_matrix()
        self.user_similarity = None
        self.item_similarity = None
    
    def _build_user_item_matrix(self) -> np.ndarray:
        n_users = len(self.user_ids)
        n_dishes = len(self.dish_ids)
        matrix = np.zeros((n_users, n_dishes))
        
        user_ratings = defaultdict(lambda: defaultdict(list))
        
        for order in self.orders:
            for item in order.items:
                if item.rating is not None:
                    user_ratings[order.user_id][item.dish_id].append(item.rating)
            
            if order.is_group_order:
                for member_id in order.group_members:
                    for item in order.items:
                        if item.rating is not None:
                            user_ratings[member_id][item.dish_id].append(item.rating * 0.7)
        
        for uid, dids in user_ratings.items():
            if uid in self.user_to_idx:
                user_idx = self.user_to_idx[uid]
                for did, ratings in dids.items():
                    if did in self.dish_to_idx:
                        dish_idx = self.dish_to_idx[did]
                        matrix[user_idx, dish_idx] = np.mean(ratings)
        
        for uid, user in self.users.items():
            if uid in self.user_to_idx:
                user_idx = self.user_to_idx[uid]
                for did in user.order_history:
                    if did in self.dish_to_idx:
                        dish_idx = self.dish_to_idx[did]
                        if matrix[user_idx, dish_idx] == 0:
                            matrix[user_idx, dish_idx] = 4.0
        
        return matrix
    
    def compute_user_similarity(self) -> np.ndarray:
        self.user_similarity = cosine_similarity(self.user_item_matrix)
        return self.user_similarity
    
    def compute_item_similarity(self) -> np.ndarray:
        self.item_similarity = cosine_similarity(self.user_item_matrix.T)
        return self.item_similarity
    
    def predict_user_based(self, user_id: str, dish_id: str, k: int = 3) -> float:
        if self.user_similarity is None:
            self.compute_user_similarity()
        
        if user_id not in self.user_to_idx or dish_id not in self.dish_to_idx:
            return 0.0
        
        user_idx = self.user_to_idx[user_id]
        dish_idx = self.dish_to_idx[dish_id]
        
        similar_users = np.argsort(self.user_similarity[user_idx])[::-1][1:k+1]
        
        total_sim = 0.0
        weighted_sum = 0.0
        
        for sim_user_idx in similar_users:
            sim = self.user_similarity[user_idx, sim_user_idx]
            rating = self.user_item_matrix[sim_user_idx, dish_idx]
            if rating > 0:
                weighted_sum += sim * rating
                total_sim += sim
        
        if total_sim > 0:
            return weighted_sum / total_sim
        return 0.0
    
    def predict_item_based(self, user_id: str, dish_id: str, k: int = 5) -> float:
        if self.item_similarity is None:
            self.compute_item_similarity()
        
        if user_id not in self.user_to_idx or dish_id not in self.dish_to_idx:
            return 0.0
        
        user_idx = self.user_to_idx[user_id]
        dish_idx = self.dish_to_idx[dish_id]
        
        rated_dishes = np.where(self.user_item_matrix[user_idx] > 0)[0]
        
        if len(rated_dishes) == 0:
            return 0.0
        
        sim_scores = self.item_similarity[dish_idx, rated_dishes]
        top_k_indices = np.argsort(sim_scores)[::-1][:k]
        
        total_sim = 0.0
        weighted_sum = 0.0
        
        for idx in top_k_indices:
            sim = sim_scores[idx]
            rating = self.user_item_matrix[user_idx, rated_dishes[idx]]
            weighted_sum += sim * rating
            total_sim += sim
        
        if total_sim > 0:
            return weighted_sum / total_sim
        return 0.0
    
    def get_user_based_recommendations(self, user_id: str, n: int = 10, 
                                        exclude_dishes: List[str] = None) -> List[Tuple[str, float]]:
        if exclude_dishes is None:
            exclude_dishes = []
        
        scores = []
        for dish_id in self.dish_ids:
            if dish_id not in exclude_dishes:
                score = self.predict_user_based(user_id, dish_id)
                scores.append((dish_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]
    
    def get_item_based_recommendations(self, user_id: str, n: int = 10,
                                        exclude_dishes: List[str] = None) -> List[Tuple[str, float]]:
        if exclude_dishes is None:
            exclude_dishes = []
        
        scores = []
        for dish_id in self.dish_ids:
            if dish_id not in exclude_dishes:
                score = self.predict_item_based(user_id, dish_id)
                scores.append((dish_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]
    
    def get_combined_recommendations(self, user_id: str, n: int = 10,
                                      exclude_dishes: List[str] = None,
                                      user_weight: float = 0.4,
                                      item_weight: float = 0.6) -> List[Tuple[str, float]]:
        if exclude_dishes is None:
            exclude_dishes = []
        
        user_recs = dict(self.get_user_based_recommendations(user_id, n=len(self.dish_ids), exclude_dishes=exclude_dishes))
        item_recs = dict(self.get_item_based_recommendations(user_id, n=len(self.dish_ids), exclude_dishes=exclude_dishes))
        
        combined_scores = {}
        for dish_id in self.dish_ids:
            if dish_id not in exclude_dishes:
                user_score = user_recs.get(dish_id, 0)
                item_score = item_recs.get(dish_id, 0)
                combined = user_score * user_weight + item_score * item_weight
                if combined > 0:
                    combined_scores[dish_id] = combined
        
        sorted_scores = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:n]
    
    def get_similar_users(self, user_id: str, k: int = 5) -> List[Tuple[str, float]]:
        if self.user_similarity is None:
            self.compute_user_similarity()
        
        if user_id not in self.user_to_idx:
            return []
        
        user_idx = self.user_to_idx[user_id]
        similar_indices = np.argsort(self.user_similarity[user_idx])[::-1][1:k+1]
        
        result = []
        for idx in similar_indices:
            sim_uid = self.user_ids[idx]
            sim_score = self.user_similarity[user_idx, idx]
            result.append((sim_uid, sim_score))
        
        return result
    
    def get_similar_dishes(self, dish_id: str, k: int = 5) -> List[Tuple[str, float]]:
        if self.item_similarity is None:
            self.compute_item_similarity()
        
        if dish_id not in self.dish_to_idx:
            return []
        
        dish_idx = self.dish_to_idx[dish_id]
        similar_indices = np.argsort(self.item_similarity[dish_idx])[::-1][1:k+1]
        
        result = []
        for idx in similar_indices:
            sim_did = self.dish_ids[idx]
            sim_score = self.item_similarity[dish_idx, idx]
            result.append((sim_did, sim_score))
        
        return result
